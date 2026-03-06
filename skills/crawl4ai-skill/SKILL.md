---
name: crawl4ai-skill
description: Crawls websites and extracts (scrapes) web page content including text, tables, lists, and images into clean LLM-friendly markdown. Use when crawling websites, scraping web content, extracting web page data for RAG/LLMs, or when the user mentions crawl4ai, web scraping, or deep crawling.
---

# When to use this skill
Use this skill to crawl a web site and scrape its contents and convert this content into clean markdown. It requires a URL to be supplied, and this URL is where crawling starts. Based on max_depth and max_pages configurations additional web pages may be crawled in addition to the start URL.

## General Steps
- 1. import needed crawl4ai modules
- 2. define crawler configuration by defining a CrawlerRunConfig; this sets the crawling strategy
- 3. define an AsyncWebCrawler() and set its crawler configurations and start URL to crawl
- 4. call the AsyncWebCrawler's "arun" function to asynchronously start the crawl
- 5. loop through a LIST of CrawlResults returned by the crawler

## Crawling Strategies
- 1. BFSDeepCrawlStrategy (Breadth-First Search) explores all links at one depth (meaning on the same level) before moving deeper

- 2. DFSDeepCrawlStrategy (Depth-First Search) explores as far down a branch as possible before backtracking to the first level and exploring another branch

- 3. BestFirstCrawlingStrategy scores pages first to prioritize the most relevant pages and scrapes content from higher scoring pages before lower scoring ones, and it uses max_pages to know when to stop crawling so low-scoring pages may be skipped; this strategy requires a scorer to be configured to set criteria for scoring pages

## Key Crawler Settings
- max_depth = number of levels deep to crawl from page where crawling starts
- include_external = stay within the same domain or allow crawls outside it
- max_pages = maximum number of pages to crawl (good to prevent over-crawling)
- score_threshold = minimum score a URL must have to be crawled and is helpful to prevent crawling low-value pages (not used with BestFirstCrawlingStrategy)

## Example code setting crawler settings

```python
strategy = DFSDeepCrawlStrategy(
    max_depth=2,               # Crawl initial page + 2 levels deep
    include_external=False,    # Stay within the same domain
    max_pages=30,              # Maximum number of pages to crawl (optional)
    score_threshold=0.5,       # Minimum score for URLs to be crawled (optional)
)
```

## Output (CrawlResult object)
- When you call arun() on a page, Crawl4AI returns a CrawlResult object containing everything you might need
- CrawlResult properties include: raw HTML, a cleaned version, optional screenshots or PDFs, structured extraction results, and more
- markdown property of CrawlResult is a MarkdownGenerationResult object and is used to access the markdown and filtered markdown

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

## Additional Resources
- For usage examples, see [examples.md](examples.md)
- [Crawl4AI documentation](https://docs.crawl4ai.com/)
- [Deep crawling documentation](https://docs.crawl4ai.com/core/deep-crawling/)