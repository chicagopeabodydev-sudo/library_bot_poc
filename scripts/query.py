#!/usr/bin/env python3
"""
Query the Supabase-backed LlamaIndex store using QUERY_TEXT.

Reads configuration from environment variables:
  DATABASE_URL    - PostgreSQL connection string for Supabase (required)
  OPENAI_API_KEY  - Used for retrieval and response generation (required)
  QUERY_TEXT      - User question to answer (required for CLI fallback)
"""

import logging
import sys
from typing import Any
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on path so we can import sibling script modules.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.rag import COLLECTION_NAME, configure_llamaindex, get_required_env, load_vector_index

SIMILARITY_TOP_K = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_query_engine(*, database_url: str | None = None, similarity_top_k: int = SIMILARITY_TOP_K) -> Any:
    """Create a query engine backed by the shared Supabase vector store."""
    configure_llamaindex(enable_llm=True)
    index = load_vector_index(database_url=database_url)
    return index.as_query_engine(similarity_top_k=similarity_top_k)


def run_query(
    query_text: str,
    *,
    query_engine: Any | None = None,
    database_url: str | None = None,
    similarity_top_k: int = SIMILARITY_TOP_K,
) -> Any:
    """Run a single query using either a provided or newly built engine."""
    normalized_query = query_text.strip()
    if not normalized_query:
        raise ValueError("Query text must not be empty")

    engine = query_engine or build_query_engine(
        database_url=database_url,
        similarity_top_k=similarity_top_k,
    )
    return engine.query(normalized_query)


def extract_sources(response: Any, *, max_excerpt_chars: int = 500) -> list[dict[str, Any]]:
    """Extract source metadata and excerpts from a LlamaIndex response."""
    sources: list[dict[str, Any]] = []

    for index, source_node in enumerate(getattr(response, "source_nodes", []), start=1):
        node = getattr(source_node, "node", source_node)
        metadata = dict(getattr(node, "metadata", {}) or {})

        try:
            content = node.get_content().strip()
        except (AttributeError, TypeError):
            content = str(getattr(node, "text", "")).strip()

        excerpt = content[:max_excerpt_chars].strip()
        if len(content) > max_excerpt_chars:
            excerpt = f"{excerpt}..."

        source_label = (
            metadata.get("file_name")
            or metadata.get("source")
            or metadata.get("url")
            or f"Source {index}"
        )

        sources.append(
            {
                "label": str(source_label),
                "score": getattr(source_node, "score", None),
                "excerpt": excerpt,
                "metadata": metadata,
            }
        )

    return sources


def main() -> None:
    """Query the existing vector store and print the response."""
    load_dotenv(override=True)

    try:
        database_url = get_required_env("DATABASE_URL")
        query_text = get_required_env("QUERY_TEXT")
    except ValueError as exc:
        logger.error("%s", exc)
        raise SystemExit(1)

    logger.info("Connecting to Supabase collection '%s'", COLLECTION_NAME)
    logger.info("Running query with similarity_top_k=%d", SIMILARITY_TOP_K)
    response = run_query(query_text, database_url=database_url, similarity_top_k=SIMILARITY_TOP_K)

    logger.info("Query complete. Retrieved %d source nodes", len(getattr(response, "source_nodes", [])))
    print(str(response))


if __name__ == "__main__":
    main()
