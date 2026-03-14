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

## Indexing

Load markdown from `website-markdown/`, create embeddings, and store in Supabase pgvector:

```bash
# After crawling (website-markdown/ must contain .md files)
# Configure .env with DATABASE_URL and OPENAI_API_KEY
python scripts/index.py
```

Environment variables:
- `DATABASE_URL` - PostgreSQL connection string for Supabase (required)
- `OPENAI_API_KEY` - Used for embeddings (required)

Get the connection string from Supabase: Project Settings → Database → Connection string (URI).

## Tests

Run tests from the project root:

```bash
pytest tests/ -v
# or run only integration tests:
pytest tests/integration/ -v
```

The crawl integration test (`tests/integration/test_crawl.py`) performs real HTTP requests and requires `.env` with `CRAWL_URL` configured. If `.env` is missing or `CRAWL_URL` is not set, the test is skipped with a warning.