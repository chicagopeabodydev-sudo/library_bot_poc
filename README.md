# library_bot_poc

A RAG system with a chatbot. Content is crawled from a website and indexed for retrieval.

NeMo Guardrails dependency and environment settings are included to prepare for adding input, retrieval, and output guardrails to the question-answering flow. The current runtime does not apply those guardrails yet.

## Streamlit UI

Ask questions in a local browser UI backed by the existing Supabase/LlamaIndex index:

```bash
# After indexing
streamlit run streamlit_app.py
```

The Streamlit app:
- reads `DATABASE_URL` and `OPENAI_API_KEY` from `.env`
- accepts each question in the browser instead of from `QUERY_TEXT`
- queries the existing `website_docs` vector collection
- shows the answer and the retrieved source snippets

Expected flow:
1. `python scripts/crawl.py`
2. `python scripts/index.py`
3. `streamlit run streamlit_app.py`

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
- `CRAWL_OUTPUT_DIR` - Directory for crawled markdown (default: `website-markdown`)
- `CRAWL_CLEAR_OUTPUT` - Clear existing markdown before crawling (default: `1`)
- `CRAWL_RUN_INDEX` - Run indexing automatically after crawl (default: `1`)

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

## Querying

Query the existing Supabase-backed index with LlamaIndex from the command line:

```bash
# After indexing
# Configure .env with DATABASE_URL, OPENAI_API_KEY, and QUERY_TEXT
python scripts/query.py
```

Environment variables:
- `DATABASE_URL` - PostgreSQL connection string for Supabase (required)
- `OPENAI_API_KEY` - Used for retrieval and response generation (required)
- `QUERY_TEXT` - Optional non-UI fallback question for the CLI script

The CLI script is useful for quick debugging, but the primary question-answering workflow is the Streamlit UI. The current app uses a chat-style interface over single-turn retrieval and does not yet implement conversational memory or streaming.

## Guardrails Configuration

The repository is prepared for a NeMo Guardrails configuration that will live in `guardrails/` by default.

Install dependencies from `requirements.txt`, which now includes `nemoguardrails[openai]` so NeMo Guardrails uses the existing OpenAI model setup for this project.

Environment variables:
- `GUARDRAILS_ENABLED` - Enables or disables guardrail integration once the runtime wiring is added. Suggested values are `1` or `0`.
- `GUARDRAILS_CONFIG_DIR` - Directory that will contain the NeMo Guardrails config files. Default example value: `guardrails`

Planned guardrailed runtime flow:
1. Accept the user question in Streamlit or from `QUERY_TEXT`.
2. Apply input guardrails to the question.
3. Retrieve candidate context from the existing Supabase-backed index.
4. Apply retrieval guardrails to the retrieved RAG content.
5. Generate an answer with the existing OpenAI-backed query model.
6. Apply output guardrails to the final answer before returning it to the user.

At this stage, the configuration surface is documented and available in `.env.example`, but the runtime query flow still behaves as described in the sections above.

## Tests

Run tests from the project root:

```bash
pytest tests/ -v
# or run only integration tests:
pytest tests/integration/ -v
```

The crawl integration test (`tests/integration/test_crawl.py`) performs real HTTP requests and requires `.env` with `CRAWL_URL` configured. If `.env` is missing or `CRAWL_URL` is not set, the test is skipped with a warning.