#!/usr/bin/env python3
"""
Crawl a website using Crawl4AI and save markdown to website-markdown/.

Reads configuration from environment variables:
  CRAWL_URL        - Home page URL to start crawling (required)
  CRAWL_MAX_DEPTH  - Max depth levels to crawl (default: 2)
  CRAWL_MAX_PAGES  - Max number of pages to crawl (default: 30)
  CRAWL_OUTPUT_DIR  - Output directory for markdown files (default: website-markdown)
  CRAWL_RUN_INDEX   - If 1 (default), run indexing after crawl; if 0, skip indexing
  CRAWL_CLEAR_OUTPUT - If 1 (default), clear output dir before crawling; if 0, do not clear
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig, LLMExtractionStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from pydantic import ValidationError

# Ensure project root is on path so we can import src.index
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.index import main as run_index
from src.models import LibraryEvent, LibraryEventExtractionResult

OUTPUT_DIR = "website-markdown"
EVENT_HINT_TERMS = (
    "event",
    "events",
    "calendar",
    "program",
    "programs",
    "storytime",
    "book club",
    "reading",
    "author talk",
    "workshop",
    "class",
    "teen night",
    "game night",
)
EVENT_EXTRACTION_INSTRUCTION = """
Extract library events from this webpage.

Return JSON that matches the provided schema exactly.
If the page does not actually describe library events, return {"events": []}.
Only include events that are clearly supported by the source page.
Use the canonical target_age_group values adult, teen, or kids.
Prefer a direct event-details or registration URL from the page for link_to_details.
""".strip()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def url_to_slug(url: str, index: int = 0) -> str:
    """Convert URL to a safe filename slug."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_") or "index"
    slug = f"{domain}_{path}" if path != "index" else domain
    slug = re.sub(r"[^\w\-]", "_", slug)
    slug = slug[:80] or "page"
    if index > 0:
        slug = f"{slug}_{index}"
    return f"{slug}.md"


def extract_markdown(result) -> str:
    """Extract markdown string from CrawlResult.markdown (str or MarkdownGenerationResult)."""
    md = result.markdown
    if md is None:
        return ""
    if hasattr(md, "raw_markdown"):
        return md.fit_markdown or md.raw_markdown or ""
    return str(md)


def get_result_title(result: Any, markdown: str) -> str:
    """Best-effort page title for heuristics and logs."""
    metadata = getattr(result, "metadata", None) or {}
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped:
            return stripped[:120]
    return ""


def is_event_like_page(result: Any, markdown: str) -> bool:
    """Use conservative heuristics so extraction only runs on likely event pages."""
    url = str(getattr(result, "url", "") or "").lower()
    title = get_result_title(result, markdown).lower()
    content_sample = markdown[:4000].lower()
    haystack = " ".join(part for part in (url, title, content_sample) if part)

    matches = sum(1 for term in EVENT_HINT_TERMS if term in haystack)
    if matches >= 2:
        return True

    high_signal_patterns = (
        "/events",
        "/calendar",
        "storytime",
        "book club",
        "game night",
        "author talk",
    )
    return any(pattern in haystack for pattern in high_signal_patterns)


def build_event_extraction_config(openai_api_key: str) -> CrawlerRunConfig:
    """Build a single-page Crawl4AI extraction config for event pages."""
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=openai_api_key,
        ),
        schema=LibraryEventExtractionResult.model_json_schema(),
        extraction_type="schema",
        instruction=EVENT_EXTRACTION_INSTRUCTION,
        chunk_token_threshold=1200,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.0, "max_tokens": 1200},
    )
    return CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),
        extraction_strategy=extraction_strategy,
        verbose=True,
    )


def parse_event_extraction_result(extracted_content: str | None) -> LibraryEventExtractionResult | None:
    """Validate Crawl4AI extraction output against the canonical schema."""
    if not extracted_content:
        return None

    try:
        payload = json.loads(extracted_content)
    except json.JSONDecodeError:
        logger.warning("Event extraction returned invalid JSON")
        return None

    if isinstance(payload, list):
        payload = {"events": payload}
    elif isinstance(payload, dict) and "events" not in payload:
        event_keys = {
            "event_type",
            "event_title",
            "date_time",
            "target_age_group",
            "location",
            "description",
            "link_to_details",
        }
        if event_keys.intersection(payload.keys()):
            payload = {"events": [payload]}

    try:
        return LibraryEventExtractionResult.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Event extraction did not match schema: %s", exc)
        return None


def format_event_markdown(events: list[LibraryEvent]) -> str:
    """Add structured event details to markdown so RAG can retrieve them reliably."""
    if not events:
        return ""

    lines = [
        "## Extracted Event Records",
        "",
        "The following structured event data was extracted from this page:",
        "",
    ]
    for event in events:
        event_data = event.model_dump(mode="json")
        lines.extend(
            [
                f"### {event_data['event_title']}",
                f"- Event type: {event_data['event_type']}",
                f"- Date/time: {event_data['date_time']}",
                f"- Target age group: {event_data['target_age_group']}",
                f"- Location: {event_data['location']}",
                f"- Description: {event_data['description']}",
                f"- Details link: {event_data['link_to_details']}",
                "",
            ]
        )
    return "\n".join(lines).strip()


async def extract_events_for_result(
    crawler: AsyncWebCrawler,
    result: Any,
    openai_api_key: str | None,
) -> LibraryEventExtractionResult | None:
    """Run a second Crawl4AI pass only for pages that appear event-related."""
    if not openai_api_key:
        logger.warning(
            "Skipping event extraction for %s because OPENAI_API_KEY is not set",
            result.url,
        )
        return None

    extraction_config = build_event_extraction_config(openai_api_key)
    extraction_result = await crawler.arun(url=result.url, config=extraction_config)  # type: ignore[arg-type]
    parsed = parse_event_extraction_result(getattr(extraction_result, "extracted_content", None))
    if parsed is None:
        return None
    return parsed


def write_event_sidecar(filepath: Path, extraction: LibraryEventExtractionResult) -> None:
    """Persist structured event data next to the markdown file."""
    sidecar_path = filepath.with_suffix(".json")
    sidecar_path.write_text(
        json.dumps(extraction.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote %s", sidecar_path)


async def main() -> None:
    load_dotenv()

    url = os.environ.get("CRAWL_URL")
    if not url:
        logger.error("CRAWL_URL environment variable is required")
        raise SystemExit(1)

    max_depth = int(os.environ.get("CRAWL_MAX_DEPTH", "2"))
    max_pages = int(os.environ.get("CRAWL_MAX_PAGES", "30"))
    output_dir = os.environ.get("CRAWL_OUTPUT_DIR", OUTPUT_DIR)

    logger.info("Starting crawl: url=%s max_depth=%s max_pages=%s", url, max_depth, max_pages)

    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            include_external=False,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_path.resolve())

    if os.environ.get("CRAWL_CLEAR_OUTPUT", "1") != "0":
        cleared = list(output_path.glob("*.md")) + list(output_path.glob("*.json"))
        for f in cleared:
            f.unlink()
        if cleared:
            logger.info("Cleared %d existing files from %s", len(cleared), output_path)

    openai_api_key = os.environ.get("OPENAI_API_KEY")

    async with AsyncWebCrawler() as crawler:
        raw_results = await crawler.arun(url, config=config)  # type: ignore

        # arun returns a list for deep crawls, or single result for single-page
        results = raw_results if isinstance(raw_results, list) else [raw_results]

        written = 0
        extracted_event_pages = 0
        seen_slugs: dict[str, int] = {}

        for result in results:
            if not result.success:
                logger.warning("Skipping failed crawl: url=%s error=%s", result.url, result.error_message)
                continue

            markdown = extract_markdown(result)
            if not markdown.strip():
                logger.warning("Skipping empty markdown: url=%s", result.url)
                continue

            base_slug = url_to_slug(result.url, index=0)
            slug_key = base_slug.removesuffix(".md")
            seen_slugs[slug_key] = seen_slugs.get(slug_key, 0) + 1
            count = seen_slugs[slug_key]
            filename = url_to_slug(result.url, index=count - 1) if count > 1 else base_slug

            filepath = output_path / filename
            page_title = get_result_title(result, markdown)
            event_extraction: LibraryEventExtractionResult | None = None

            if is_event_like_page(result, markdown):
                logger.info("Detected event-like page: url=%s title=%s", result.url, page_title or "<unknown>")
                event_extraction = await extract_events_for_result(crawler, result, openai_api_key)
                if event_extraction and event_extraction.events:
                    extracted_event_pages += 1
                    event_markdown = format_event_markdown(event_extraction.events)
                    if event_markdown:
                        markdown = f"{event_markdown}\n\n---\n\n{markdown}"
                    write_event_sidecar(filepath, event_extraction)
                else:
                    logger.info("No structured events extracted for %s", result.url)

            filepath.write_text(markdown, encoding="utf-8")
            written += 1
            logger.info("Wrote %s (%d bytes)", filepath, len(markdown))

    logger.info(
        "Crawl complete: %d pages crawled, %d files written, %d event pages enriched",
        len(results),
        written,
        extracted_event_pages,
    )

    if written > 0 and os.environ.get("CRAWL_RUN_INDEX", "1") != "0":
        run_index()


if __name__ == "__main__":
    asyncio.run(main())
