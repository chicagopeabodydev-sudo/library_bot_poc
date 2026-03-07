# library_bot_poc

A RAG system with a chatbot. Content is crawled from a website and indexed for retrieval.

## Crawling

Crawl a website and save markdown to `website-markdown/`:

```bash
# Create venv and install dependencies
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Install browser (required for crawl4ai)
playwright install chromium

# Configure and run
cp .env.example .env
# Edit .env: set CRAWL_URL, CRAWL_MAX_DEPTH, CRAWL_MAX_PAGES
python scripts/crawl.py
```

Environment variables (see `.env.example`):
- `CRAWL_URL` - Home page URL to crawl (required)
- `CRAWL_MAX_DEPTH` - Max depth levels (default: 2)
- `CRAWL_MAX_PAGES` - Max pages to crawl (default: 30)