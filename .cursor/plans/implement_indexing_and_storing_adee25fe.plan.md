---
name: Implement Indexing and Storing
overview: "Implement indexing with LlamaIndex: load markdown files from website-markdown/, create vector embeddings, and store the index in Supabase pgvector using credentials from environment variables."
todos: []
isProject: false
---

# Plan 2: Implement Indexing and Storing

## Scope

Build the indexing pipeline that:

1. Loads markdown files from the `website-markdown/` folder (created by the crawling plan)
2. Uses LlamaIndex to parse, chunk, embed, and index the content
3. Stores the index (embeddings) in a Supabase-hosted pgvector database using env-based credentials

## Prerequisites

- Plan 1 (crawling) completed; `website-markdown/` contains `.md` files
- Supabase project with pgvector enabled
- OpenAI API key (for embeddings; LlamaIndex default)

## Architecture

```mermaid
flowchart LR
    MD[website-markdown/*.md] --> Load[LlamaIndex load]
    Load --> Parse[MarkdownNodeParser]
    Parse --> Embed[Embedding model]
    Embed --> Store[SupabaseVectorStore]
    Env[.env: DATABASE_URL, etc.] --> Store
```



## Implementation Steps

### 1. Dependencies and Config

- **Add to** `[requirements.txt](requirements.txt)`: `llama-index`, `llama-index-vector-stores-supabase`, `llama-index-embeddings-openai`, `python-dotenv`, `openai`
- **Add to** `.env.example`:

```
  DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
  OPENAI_API_KEY=sk-...
  

```

- Supabase connection string from: Project Settings → Database → Connection string (URI)

### 2. Indexer Script

Create `scripts/index.py` (or `src/indexer.py` with `__main__`) that:

**Step 1 – Load markdown from `website-markdown/`:**

- Use `SimpleDirectoryReader` with `input_dir="website-markdown"` and `required_exts=[".md"]`, or iterate over `website-markdown/*.md` and build `Document` objects with metadata (e.g. `source` = filename/URL)
- Per [llama-index-skill](skills/llama-index-skill/SKILL.md): documents are the input; nodes are produced by a node parser

**Step 2 – Parse and chunk:**

- Use `MarkdownNodeParser().get_nodes_from_documents(documents)` to chunk markdown into nodes

**Step 3 – Create vector store and index:**

- Initialize `SupabaseVectorStore` from `llama_index.vector_stores.supabase`:

```python
  vector_store = SupabaseVectorStore(
      postgres_connection_string=os.environ["DATABASE_URL"],
      collection_name="website_docs",
      dimension=1536  # OpenAI text-embedding-3-small
  )
  

```

- Create `StorageContext.from_defaults(vector_store=vector_store)`
- Build index: `VectorStoreIndex.from_documents(documents, storage_context=storage_context)` (LlamaIndex will parse, embed, and store automatically), or `from_nodes(nodes, storage_context=...)` if using pre-parsed nodes

**Step 4 – Persist:**

- Index creation writes embeddings to Supabase; no extra persist step needed if using `from_documents`/`from_nodes` with the vector store

### 3. Environment Variables


| Variable         | Purpose                                               |
| ---------------- | ----------------------------------------------------- |
| `DATABASE_URL`   | PostgreSQL connection string for Supabase (pgvector)  |
| `OPENAI_API_KEY` | Used by LlamaIndex for embeddings (and later for LLM) |


### 4. Collection and Dimension

- **Collection name**: e.g. `website_docs` (configurable via env if desired)
- **Dimension**: `1536` for OpenAI `text-embedding-3-small` (default); use `384` if switching to `all-MiniLM-L6-v2`

### 5. Error Handling

- Ensure `website-markdown/` exists and has `.md` files before indexing
- Validate `DATABASE_URL` and `OPENAI_API_KEY` are set
- Log progress (e.g. documents loaded, nodes created)

## Key Files


| File               | Purpose                                                     |
| ------------------ | ----------------------------------------------------------- |
| `scripts/index.py` | Entry point: load markdown, create index, store in Supabase |
| `requirements.txt` | LlamaIndex, Supabase vector store, OpenAI embeddings        |
| `.env.example`     | `DATABASE_URL`, `OPENAI_API_KEY`                            |


## Reference

- [llama-index-skill SKILL.md](skills/llama-index-skill/SKILL.md) – Load, index, store flow; MarkdownNodeParser; VectorStoreIndex
- [llama-index-skill examples.md](skills/llama-index-skill/examples.md) – ChromaDB example (same pattern for Supabase)
- [supabase-skill SKILL.md](skills/supabase-skill/SKILL.md) – vecs/pgvector; LlamaIndex integration link
- [Supabase LlamaIndex integration](https://supabase.com/docs/guides/ai/integrations/llamaindex)

