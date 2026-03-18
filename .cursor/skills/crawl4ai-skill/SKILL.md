---
name: crawl4ai-skill
description: Crawls websites and extracts (scrapes) web page content including text, tables, lists, and images into clean LLM-friendly markdown. Use when crawling websites, scraping web content, extracting web page data for RAG/LLMs, or when the user mentions crawl4ai, web scraping, or deep crawling.
---

# When to use this skill
Use this skill to crawl a website, scrape its contents, and convert that content into clean markdown. It requires a starting URL. Depending on `max_depth`, `max_pages`, and the chosen crawl strategy, Crawl4AI can either crawl a single page or continue to additional pages beyond the start URL.

## General Steps
1. Import the needed Crawl4AI modules.
2. Define a `CrawlerRunConfig` with the crawl strategy and crawl settings you need.
3. Create an `AsyncWebCrawler` and pass any browser-level configuration if needed.
4. Call `AsyncWebCrawler.arun(...)` to start the crawl.
5. Handle the returned result:
   If you run a single-page crawl, `arun(...)` returns one `CrawlResult`.
   If you run a deep crawl, `arun(...)` returns a list of `CrawlResult` objects.

## Crawling Strategies
1. `BFSDeepCrawlStrategy` (Breadth-First Search) explores all links at one depth before moving deeper.
2. `DFSDeepCrawlStrategy` (Depth-First Search) explores as far down one branch as possible before backtracking.
3. `BestFirstCrawlingStrategy` scores pages to prioritize the most relevant pages first. This strategy requires a scorer configuration so pages can be ranked before crawling.

## Key Crawler Settings
- `max_depth` = number of levels deep to crawl from the starting page
- `include_external` = stay within the same domain or allow crawls outside it
- `max_pages` = maximum number of pages to crawl
- `score_threshold` = minimum score a URL must have to be crawled when using a scoring-based strategy

## Example code setting crawler settings

```python
from crawl4ai.deep_crawling import DFSDeepCrawlStrategy

strategy = DFSDeepCrawlStrategy(
    max_depth=2,               # Crawl initial page + 2 levels deep
    include_external=False,    # Stay within the same domain
    max_pages=30,              # Maximum number of pages to crawl (optional)
    score_threshold=0.5,       # Minimum score for URLs to be crawled (optional)
)
```

## Output (CrawlResult object)
- When you call `arun()` on a page, Crawl4AI returns a `CrawlResult` object containing the crawl output.
- `CrawlResult` properties include raw HTML, cleaned HTML, optional screenshots or PDFs, structured extraction results, and more.
- The `markdown` property may contain a `MarkdownGenerationResult`, which gives access to variants such as `raw_markdown` and `fit_markdown`.

### CrawlResult classes and properties

```python
# Pydantic BaseModel syntax
class MarkdownGenerationResult(BaseModel):
    raw_markdown: str
    markdown_with_citations: str
    references_markdown: str
    fit_markdown: Optional[str] = None
    fit_html: Optional[str] = None

class CrawlResult(BaseModel):
    url: str
    html: str
    fit_html: Optional[str] = None
    success: bool
    cleaned_html: Optional[str] = None
    media: Dict[str, List[Dict]] = {}
    links: Dict[str, List[Dict]] = {}
    downloaded_files: Optional[List[str]] = None
    js_execution_result: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    pdf: Optional[bytes] = None
    mhtml: Optional[str] = None
    markdown: Optional[Union[str, MarkdownGenerationResult]] = None
    extracted_content: Optional[str] = None
    metadata: Optional[dict] = None
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    response_headers: Optional[dict] = None
    status_code: Optional[int] = None
    ssl_certificate: Optional[SSLCertificate] = None
    dispatch_result: Optional[DispatchResult] = None
    redirected_url: Optional[str] = None
    redirected_status_code: Optional[int] = None
    network_requests: Optional[List[Dict[str, Any]]] = None
    console_messages: Optional[List[Dict[str, Any]]] = None
    tables: List[Dict] = Field(default_factory=list)
```

---

## LLM Extraction
Use LLM extraction when you want Crawl4AI to structure results according to a supplied schema, usually a Pydantic model.

### Steps
1. Chunking (optional): The HTML or markdown is split into smaller segments if it is very long.
2. Prompt construction: For each chunk, Crawl4AI builds a prompt that includes your instruction and optional schema.
3. LLM inference: Each chunk is sent to the model, either in parallel or sequentially.
4. Combining: The results from each chunk are merged and parsed into JSON.

Extraction types:
- `"schema"`: The model tries to return JSON conforming to your Pydantic-based schema. You provide `schema=YourPydanticModel.model_json_schema()`.
- `"block"`: The model returns freeform text or smaller JSON structures, which the library collects.

```python
import os

from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai import LLMExtractionStrategy

# step 1 - define a Pydantic model
class Product(BaseModel):
    name: str
    price: str

# step 2 - assign the Pydantic model to "schema" of LLMExtractionStrategy
async def main():
    llm_strategy = LLMExtractionStrategy(
        llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv('OPENAI_API_KEY')),
        schema=Product.model_json_schema(), # Or use model_json_schema()
        extraction_type="schema",
        instruction="Extract all product objects with 'name' and 'price' from the content.",
        chunk_token_threshold=1000,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="markdown",   # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 800}
    )

    # remaining crawler code here...
```

---

## Additional Resources
- For usage examples, see [examples.md](examples.md)
- [Crawl4AI documentation](https://docs.crawl4ai.com/)
- [Deep crawling documentation](https://docs.crawl4ai.com/core/deep-crawling/)
- [Simple crawling](https://docs.crawl4ai.com/core/simple-crawling/)
- [Browser, crawler, and LLM configuration](https://docs.crawl4ai.com/core/browser-crawler-config/)
- [Markdown generation](https://docs.crawl4ai.com/core/markdown-generation/)
- [Command line interface](https://docs.crawl4ai.com/core/cli/)
- [LLM extraction](https://docs.crawl4ai.com/extraction/llm-strategies/)