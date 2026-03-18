#!/usr/bin/env python3
"""
Query the Supabase-backed LlamaIndex store using QUERY_TEXT.

Reads configuration from environment variables:
  DATABASE_URL    - PostgreSQL connection string for Supabase (required)
  OPENAI_API_KEY  - Used for retrieval and response generation (required)
  QUERY_TEXT      - User question to answer (required for CLI fallback)
"""

from dataclasses import dataclass
import logging
import sys
from typing import Any
from pathlib import Path

try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False

from llama_index.core import get_response_synthesizer  # pyright: ignore[reportMissingImports]
from llama_index.core.response_synthesizers import ResponseMode  # pyright: ignore[reportMissingImports]
from llama_index.core.schema import QueryBundle  # pyright: ignore[reportMissingImports]

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


@dataclass
class QueryPipeline:
    """Shared retrieval and synthesis components for answering queries."""

    retriever: Any
    response_synthesizer: Any


def normalize_query_text(query_text: str) -> str:
    """Validate and normalize user query text."""
    normalized_query = query_text.strip()
    if not normalized_query:
        raise ValueError("Query text must not be empty")
    return normalized_query


def build_retriever(*, database_url: str | None = None, similarity_top_k: int = SIMILARITY_TOP_K) -> Any:
    """Create a retriever backed by the shared Supabase vector store."""
    configure_llamaindex(enable_llm=False)
    index = load_vector_index(database_url=database_url)
    return index.as_retriever(similarity_top_k=similarity_top_k)


def build_response_synthesizer() -> Any:
    """Create the shared response synthesizer used after retrieval."""
    configure_llamaindex(enable_llm=True)
    return get_response_synthesizer(response_mode=ResponseMode.COMPACT)


def build_query_engine(*, database_url: str | None = None, similarity_top_k: int = SIMILARITY_TOP_K) -> Any:
    """Create reusable retrieval and synthesis components for querying."""
    configure_llamaindex(enable_llm=True)
    index = load_vector_index(database_url=database_url)
    return QueryPipeline(
        retriever=index.as_retriever(similarity_top_k=similarity_top_k),
        response_synthesizer=get_response_synthesizer(response_mode=ResponseMode.COMPACT),
    )


def retrieve_nodes(
    query_text: str,
    *,
    retriever: Any | None = None,
    database_url: str | None = None,
    similarity_top_k: int = SIMILARITY_TOP_K,
) -> list[Any]:
    """Retrieve source nodes for a normalized query before synthesis."""
    normalized_query = normalize_query_text(query_text)
    active_retriever = retriever or build_retriever(
        database_url=database_url,
        similarity_top_k=similarity_top_k,
    )
    return active_retriever.retrieve(QueryBundle(query_str=normalized_query))


def synthesize_response(
    query_text: str,
    nodes: list[Any],
    *,
    response_synthesizer: Any | None = None,
) -> Any:
    """Synthesize a final answer from the approved retrieved nodes."""
    normalized_query = normalize_query_text(query_text)
    active_synthesizer = response_synthesizer or build_response_synthesizer()
    return active_synthesizer.synthesize(
        query=QueryBundle(query_str=normalized_query),
        nodes=nodes,
    )


def run_query(
    query_text: str,
    *,
    query_engine: Any | None = None,
    database_url: str | None = None,
    similarity_top_k: int = SIMILARITY_TOP_K,
) -> Any:
    """Run a single query by retrieving nodes and then synthesizing an answer."""
    normalized_query = normalize_query_text(query_text)

    engine = query_engine or build_query_engine(
        database_url=database_url,
        similarity_top_k=similarity_top_k,
    )

    # Preserve compatibility with any legacy caller that still passes a
    # LlamaIndex query engine instead of the new QueryPipeline wrapper.
    if hasattr(engine, "query") and not isinstance(engine, QueryPipeline):
        return engine.query(normalized_query)

    nodes = retrieve_nodes(
        normalized_query,
        retriever=engine.retriever,
    )
    return synthesize_response(
        normalized_query,
        nodes,
        response_synthesizer=engine.response_synthesizer,
    )


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


def run_guardrailed_query_for_cli(
    query_text: str,
    *,
    query_pipeline: QueryPipeline | Any | None = None,
    database_url: str | None = None,
    similarity_top_k: int = SIMILARITY_TOP_K,
) -> Any:
    """Run the shared guardrailed query flow for CLI callers."""
    from scripts.guardrails import run_guardrailed_query

    return run_guardrailed_query(
        query_text,
        query_pipeline=query_pipeline,
        database_url=database_url,
        similarity_top_k=similarity_top_k,
    )


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
    try:
        result = run_guardrailed_query_for_cli(
            query_text,
            database_url=database_url,
            similarity_top_k=SIMILARITY_TOP_K,
        )
    except Exception as exc:
        logger.error("Query failed: %s", exc)
        raise SystemExit(1)

    logger.info("Query complete. Retrieved %d approved source nodes", len(getattr(result, "source_nodes", [])))
    if getattr(result, "blocked", False):
        logger.info("Guardrails blocked the query at stage '%s'", getattr(result, "block_stage", "unknown"))
    print(result.answer_text)


if __name__ == "__main__":
    main()
