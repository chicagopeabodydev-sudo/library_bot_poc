# supabase-skill Examples

Examples for Supabase pgvector (vecs) and general Supabase client usage.

---

## Example 1 - Supabase client (general Postgres)

Connect to Supabase for tables, auth, and storage.

```python
import os
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Fetch data
response = supabase.table("planets").select("*").execute()
```

---

## Example 2 - vecs client and collection

Create a vecs client and get or create a vector collection. Use your Supabase database connection string (Project Settings → Database → URI).

```python
import vecs

DB_CONNECTION = "postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"
vx = vecs.create_client(DB_CONNECTION)

# Get or create collection (dimension must match your embedding model, e.g. 384 for all-MiniLM, 1536 for OpenAI)
docs = vx.get_or_create_collection(name="docs", dimension=384)
```

---

## Example 3 - Upsert vectors

Add or update vector records. Each record is `(id, vector, metadata)`.

```python
docs.upsert(
    records=[
        ("doc_1", [0.1, 0.2, 0.3, ...], {"source": "guide", "year": 2024}),
        ("doc_2", [0.7, 0.8, 0.9, ...], {"source": "tutorial", "year": 2023}),
    ]
)
```

---

## Example 4 - Similarity search (query)

Query by vector. Returns matching record IDs (and optionally metadata/values).

```python
results = docs.query(
    data=[0.4, 0.5, 0.6, ...],  # Query vector
    limit=5,
    filters={},
    include_metadata=True,
    include_value=True,
)
```

---

## Example 5 - Query with metadata filters

Filter results by metadata, similar to SQL WHERE clauses.

```python
results = docs.query(
    data=[0.4, 0.5, 0.6, ...],
    limit=5,
    filters={"year": {"$eq": 2024}, "source": {"$in": ["guide", "tutorial"]}},
    include_metadata=True,
)
```

---

## Example 6 - Create index

Create an index after upserting records for faster queries. IVFFlat requires populated data; HNSW can be created on empty collections.

```python
from vecs import IndexMethod, IndexMeasure, IndexArgsHNSW

docs.create_index(
    method=IndexMethod.hnsw,
    measure=IndexMeasure.cosine_distance,
    index_arguments=IndexArgsHNSW(m=8),
)
```

---

## Example 7 - Delete records

Delete by ID or by metadata filter.

```python
# Delete by IDs
deleted = docs.delete(ids=["doc_1", "doc_2"])

# Delete by metadata filter
deleted = docs.delete(filters={"year": {"$lt": 2023}})
```

---

## Example 8 - Supabase table CRUD (optional)

For non-vector tables, use supabase-py:

```python
# Insert
supabase.table("planets").insert({"id": 1, "name": "Pluto"}).execute()

# Update
supabase.table("instruments").update({"name": "piano"}).eq("id", 1).execute()

# Delete
supabase.table("countries").delete().eq("id", 1).execute()
```
