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

        # A LIST of results is returned by arun for deep crawls
        for result in results[:3]:  # Show first 3 results
            print(f"URL: {result.url}")
            print(f"Depth: {result.metadata.get('depth', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 3 - Crawling with Content Filters

Use `FilterChain` to restrict which URLs are crawled (patterns, domains, content types).

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
