---
name: supabase-skill
description: Connects to Supabase-hosted PostgreSQL and pgvector vector databases. Use when storing or querying vector embeddings, building RAG pipelines with Supabase, using vecs for similarity search, or when the user mentions Supabase, pgvector, or vector databases.
---

# When to use this skill

Use this skill when data needs to be stored, retrieved, or managed in a Supabase-hosted database—including pgvector for vector similarity search and embeddings.

## Connecting to Supabase (supabase-py)

For general PostgreSQL operations (tables, auth, storage):

```python
import os
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
```

## OpenAI key (for embeddings)

When using OpenAI embeddings with vecs adapters, store the API key as an environment variable:

```python
import os
os.environ["OPENAI_API_KEY"] = "your_openai_api_key"
```

## Connecting to pgvector (vecs)

For vector stores, use the `vecs` client with a direct PostgreSQL connection URL:

1. Install vecs: `pip install vecs`
2. Create a client:

```python
import vecs

DB_CONNECTION = "postgresql://<user>:<password>@<host>:<port>/<db_name>"
vx = vecs.create_client(DB_CONNECTION)
```

Get your connection string from Supabase: Project Settings → Database → Connection string (URI).

## Collections

Collections are groups of vector records. Records can be added or updated via upsert. Index collections for better query performance.

**Vector record format:**

```
Record (id: String, vec: Numeric[], metadata: JSON)
```

**Underlying PostgreSQL table:**

```sql
CREATE TABLE <collection_name> (
    id TEXT PRIMARY KEY,
    vec vector(<dimension>),
    metadata jsonb
);
```

## Indexes

Indexes speed up similarity search. Only one index per collection. Create after upserting records (IVFFlat requires populated data; HNSW can be created on empty collections).

**Distance measures:** `vecs.IndexMeasure.cosine_distance` (default), `l2_distance`, `l1_distance`, `max_inner_product`

**Index methods:** `vecs.IndexMethod.auto`, `vecs.IndexMethod.hnsw`, `vecs.IndexMethod.ivfflat`

```python
from vecs import IndexMethod, IndexMeasure, IndexArgsHNSW

docs = vx.get_or_create_collection(name="docs", dimension=384)
docs.create_index(
    method=IndexMethod.hnsw,
    measure=IndexMeasure.cosine_distance,
    index_arguments=IndexArgsHNSW(m=8),
)
```

## Metadata filters

Metadata (key-value pairs on records) can filter queries, similar to SQL WHERE clauses.

**Example:** `{"year": {"$eq": 2020}}`

| Operator   | Description                                                         |
|------------|---------------------------------------------------------------------|
| `$eq`      | Matches values equal to a specified value                           |
| `$ne`      | Matches values not equal to a specified value                       |
| `$gt`      | Matches values greater than a specified value                       |
| `$gte`     | Matches values greater than or equal to a specified value           |
| `$lt`      | Matches values less than a specified value                         |
| `$lte`     | Matches values less than or equal to a specified value              |
| `$in`      | Matches values contained in a scalar list                          |
| `$contains`| Matches when a scalar is contained within an array metadata field   |

## Additional Resources

- For usage examples, see [examples.md](examples.md)
- [Supabase documentation](https://supabase.com/docs/)
- [Supabase pgvector / vecs API](https://supabase.com/docs/guides/ai/python/api)
- [LlamaIndex integration](https://supabase.com/docs/guides/ai/integrations/llamaindex)
- [Indexing vector collections](https://supabase.com/docs/guides/ai/python/indexes)
- [Metadata and filters](https://supabase.com/docs/guides/ai/python/metadata)
