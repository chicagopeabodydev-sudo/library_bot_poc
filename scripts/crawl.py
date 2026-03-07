#!/usr/bin/env python3
"""
Crawl a website using Crawl4AI and save markdown to website-markdown/.

Reads configuration from environment variables:
  CRAWL_URL       - Home page URL to start crawling (required)
  CRAWL_MAX_DEPTH - Max depth levels to crawl (default: 2)
  CRAWL_MAX_PAGES - Max number of pages to crawl (default: 30)
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

OUTPUT_DIR = "website-markdown"

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
        return md.raw_markdown or ""
    return str(md)


async def main() -> None:
    load_dotenv()

    url = os.environ.get("CRAWL_URL")
    if not url:
        logger.error("CRAWL_URL environment variable is required")
        raise SystemExit(1)

    max_depth = int(os.environ.get("CRAWL_MAX_DEPTH", "2"))
    max_pages = int(os.environ.get("CRAWL_MAX_PAGES", "30"))

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

    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_path.resolve())

    async with AsyncWebCrawler() as crawler:
        raw_results = await crawler.arun(url, config=config)

    # arun returns a list for deep crawls, or single result for single-page
    results = raw_results if isinstance(raw_results, list) else [raw_results]

    written = 0
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
        filepath.write_text(markdown, encoding="utf-8")
        written += 1
        logger.info("Wrote %s (%d bytes)", filepath, len(markdown))

    logger.info("Crawl complete: %d pages crawled, %d files written", len(results), written)


if __name__ == "__main__":
    asyncio.run(main())
