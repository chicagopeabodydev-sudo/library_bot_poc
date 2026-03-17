#!/usr/bin/env python3
"""
Shared LlamaIndex/Supabase configuration for indexing and querying.
"""

import os

from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.supabase import SupabaseVectorStore

COLLECTION_NAME = "website_docs"
EMBEDDING_DIMENSION = 1536  # OpenAI text-embedding-3-small
EMBED_MODEL_NAME = "text-embedding-3-small"
QUERY_LLM_MODEL = "gpt-4o-mini"


def get_required_env(name: str) -> str:
    """Return a required environment variable or raise a helpful error."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} environment variable is required")
    return value


def configure_llamaindex(*, enable_llm: bool = False) -> None:
    """Configure the OpenAI-backed models used by LlamaIndex."""
    api_key = get_required_env("OPENAI_API_KEY")
    Settings.embed_model = OpenAIEmbedding(
        model=EMBED_MODEL_NAME,
        api_key=api_key,
    )

    if enable_llm:
        Settings.llm = OpenAI(
            model=QUERY_LLM_MODEL,
            api_key=api_key,
        )


def create_vector_store(*, database_url: str | None = None) -> SupabaseVectorStore:
    """Create the shared Supabase vector store instance."""
    return SupabaseVectorStore(
        postgres_connection_string=database_url or get_required_env("DATABASE_URL"),
        collection_name=COLLECTION_NAME,
        dimension=EMBEDDING_DIMENSION,
    )


def create_storage_context(*, database_url: str | None = None) -> StorageContext:
    """Create a storage context backed by the shared vector store."""
    return StorageContext.from_defaults(
        vector_store=create_vector_store(database_url=database_url)
    )


def load_vector_index(*, database_url: str | None = None) -> VectorStoreIndex:
    """Reconnect to an existing vector store-backed index for querying."""
    return VectorStoreIndex.from_vector_store(
        vector_store=create_vector_store(database_url=database_url)
    )
