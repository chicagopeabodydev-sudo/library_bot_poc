# crawl4ai-skill Examples

Crawl4AI can be configured to deep crawl websites beyond a single page. It has configurations for crawl depth below the start web page (max_depth), domain boundaries (include_external), and content filtering.

---

## Example 1 - Basic Crawl

Single-page crawl with default configuration. Returns one `CrawlResult` object.

```python
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def main():
    browser_config = BrowserConfig()  # Default browser configuration
    run_config = CrawlerRunConfig()   # Default crawl run configuration

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=run_config
        )
        print(result.markdown)  # Print clean markdown content

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 2 - Breadth-First Crawling Strategy

Deep crawl using BFS. Returns a **list** of `CrawlResult` objects.

```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

async def main():
    # Configure a 2-level deep crawl
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://example.com", config=config)

        print(f"Crawled {len(results)} pages in total")

        # A list of CrawlResult objects is returned for deep crawls
        for result in results[:3]:  # Show first 3 results
            print(f"URL: {result.url}")
            print(f"Depth: {(result.metadata or {}).get('depth', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 3 - Crawling with URL Filters

Use `FilterChain` to restrict which URLs are crawled based on patterns, domains, and content types.

```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    URLPatternFilter,
    DomainFilter,
    ContentTypeFilter
)

async def main():
    # Create a chain of filters
    filter_chain = FilterChain([
        URLPatternFilter(patterns=["*guide*", "*tutorial*"]),
        DomainFilter(
            allowed_domains=["docs.example.com"],
            blocked_domains=["old.docs.example.com"]
        ),
        ContentTypeFilter(allowed_types=["text/html"])
    ])

    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,
            filter_chain=filter_chain
        )
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://docs.example.com", config=config)
        for result in results:
            print(f"URL: {result.url}")

if __name__ == "__main__":
    asyncio.run(main())
```
---

## Example 4 - Simple Markdown Generation

```python
import asyncio

from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    # Example: ignore all links, don't escape HTML, and wrap text at 80 characters
    md_generator = DefaultMarkdownGenerator(
        options={
            "ignore_links": True,
            "escape_html": False,
            "body_width": 80
        }
    )

    config = CrawlerRunConfig(
        markdown_generator=md_generator
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com/docs", config=config)
        if result.success:
            markdown = getattr(result.markdown, "raw_markdown", str(result.markdown))
            print("Markdown:\n", markdown[:500])  # Just a snippet
        else:
            print("Crawl failed:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 5 - LLM Extraction with Pydantic Model

```python
import asyncio
import json
import os

from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai import LLMExtractionStrategy

class Product(BaseModel):
    name: str
    price: str

async def main():
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv('OPENAI_API_KEY')),
        schema=Product.model_json_schema(),
        extraction_type="schema",
        instruction="Extract all product objects with 'name' and 'price' from the content.",
        chunk_token_threshold=1000,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="markdown",   # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 800}
    )

    # 2. Build the crawler config
    crawl_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS
    )

    # 3. Create a browser config if needed
    browser_cfg = BrowserConfig(headless=True)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # 4. Let's say we want to crawl a single page
        result = await crawler.arun(
            url="https://example.com/products",
            config=crawl_config
        )

        if result.success:
            # 5. The extracted content is presumably JSON
            data = json.loads(result.extracted_content)
            print("Extracted items:", data)

            # 6. Show usage stats
            llm_strategy.show_usage()  # prints token usage
        else:
            print("Error:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 6 - Best-First Crawling Strategy

Use `BestFirstCrawlingStrategy` when you want to prioritize the most relevant URLs first instead of crawling strictly by breadth or depth.

```python
import asyncio

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

async def main():
    keyword_scorer = KeywordRelevanceScorer(
        keywords=["api", "guide", "reference", "tutorial"],
        weight=0.7,
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=BestFirstCrawlingStrategy(
            max_depth=2,
            include_external=False,
            max_pages=20,
            url_scorer=keyword_scorer,
        ),
        stream=True,  # Helpful when higher-scoring pages return first
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://docs.example.com", config=config)
        for result in results[:5]:
            print(result.url)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 7 - Save Markdown Files For A RAG Pipeline

This pattern is useful when you want to crawl pages and write markdown files to disk before indexing them with a RAG tool.

```python
import asyncio
from pathlib import Path

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

OUTPUT_DIR = Path("website-markdown")

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=1,
            include_external=False,
            max_pages=10,
        )
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://example.com", config=config)

        for index, result in enumerate(results, start=1):
            if not result.success:
                continue

            markdown = getattr(result.markdown, "fit_markdown", None) or getattr(
                result.markdown, "raw_markdown", str(result.markdown)
            )
            output_path = OUTPUT_DIR / f"page_{index}.md"
            output_path.write_text(markdown, encoding="utf-8")
            print(f"Wrote {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 8 - Choose Between `raw_markdown` And `fit_markdown`

Use `raw_markdown` when you want the full page text. Use `fit_markdown` when you want a cleaner version with more boilerplate removed.

```python
import asyncio

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
    md_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(
            threshold=0.45,
            threshold_type="dynamic",
            min_word_threshold=5,
        )
    )

    config = CrawlerRunConfig(markdown_generator=md_generator)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com/docs", config=config)

        if result.success:
            raw_markdown = result.markdown.raw_markdown
            fit_markdown = result.markdown.fit_markdown

            print("Raw markdown length:", len(raw_markdown))
            print("Fit markdown length:", len(fit_markdown or ""))

            # Pick one depending on your use case:
            markdown_for_rag = fit_markdown or raw_markdown
            print(markdown_for_rag[:500])
        else:
            print("Crawl failed:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
```
