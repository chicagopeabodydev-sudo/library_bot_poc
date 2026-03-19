#!/usr/bin/env python3
"""
Load markdown from website-markdown/, index with LlamaIndex, and store in Supabase pgvector.

Reads configuration from environment variables:
  DATABASE_URL     - PostgreSQL connection string for Supabase (required)
  OPENAI_API_KEY   - Used for embeddings (required)
  CRAWL_OUTPUT_DIR - Input directory for markdown files (default: website-markdown)
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import MetadataMode, TextNode
from pydantic import ValidationError

# Ensure project root is on path so we can import sibling script modules.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.models import LibraryEventExtractionResult
from src.rag import COLLECTION_NAME, configure_llamaindex, create_storage_context, get_required_env

DEFAULT_INPUT_DIR = "website-markdown"
EMBED_CHUNK_SIZE = 1024
EMBED_CHUNK_OVERLAP = 100
EXCLUDED_METADATA_KEYS = [
    "source_path",
    "event_sidecar_path",
    "structured_events_json",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _unique_non_empty(values: list[str]) -> list[str]:
    """Preserve order while removing empty duplicates."""
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values


def load_event_sidecar(sidecar_path: Path) -> LibraryEventExtractionResult | None:
    """Load and validate a same-basename event sidecar when present."""
    if not sidecar_path.exists():
        return None

    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        return LibraryEventExtractionResult.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Skipping invalid event sidecar %s: %s", sidecar_path, exc)
        return None


def build_event_metadata(extraction: LibraryEventExtractionResult) -> dict[str, Any]:
    """Flatten structured event records into metadata-friendly fields."""
    event_payloads = [event.model_dump(mode="json") for event in extraction.events]

    return {
        "has_structured_events": bool(event_payloads),
        "event_count": len(event_payloads),
        "event_titles": " | ".join(
            _unique_non_empty([event["event_title"] for event in event_payloads])
        ),
        "event_types": " | ".join(
            _unique_non_empty([event["event_type"] for event in event_payloads])
        ),
        "event_target_age_groups": " | ".join(
            _unique_non_empty([event["target_age_group"] for event in event_payloads])
        ),
        "event_locations": " | ".join(
            _unique_non_empty([event["location"] for event in event_payloads])
        ),
        "event_dates": " | ".join(
            _unique_non_empty([str(event["date_time"]) for event in event_payloads])
        ),
        "structured_events_json": json.dumps(event_payloads, ensure_ascii=True),
    }


def load_markdown_documents(input_path: Path) -> list[Document]:
    """Load markdown files and merge optional event sidecars into metadata."""
    documents: list[Document] = []

    for md_path in sorted(input_path.glob("*.md")):
        text = md_path.read_text(encoding="utf-8").strip()
        if not text:
            logger.warning("Skipping empty markdown file %s", md_path)
            continue

        metadata: dict[str, Any] = {
            "file_name": md_path.name,
            "source_path": str(md_path),
            "has_structured_events": False,
            "event_count": 0,
        }

        sidecar_path = md_path.with_suffix(".json")
        extraction = load_event_sidecar(sidecar_path)
        if extraction and extraction.events:
            metadata["event_sidecar_path"] = str(sidecar_path)
            metadata.update(build_event_metadata(extraction))

        documents.append(
            Document(
                text=text,
                metadata=metadata,
                excluded_embed_metadata_keys=list(EXCLUDED_METADATA_KEYS),
                excluded_llm_metadata_keys=list(EXCLUDED_METADATA_KEYS),
            )
        )

    return documents


def chunk_nodes_for_embeddings(nodes: list) -> list[TextNode]:
    """Split parsed markdown nodes into embedding-safe chunks."""
    splitter = SentenceSplitter(
        chunk_size=EMBED_CHUNK_SIZE,
        chunk_overlap=EMBED_CHUNK_OVERLAP,
    )
    chunked_nodes: list[TextNode] = []

    for node in nodes:
        text = node.get_content(metadata_mode=MetadataMode.NONE).strip()
        if not text:
            continue

        chunks = splitter.split_text_metadata_aware(
            text,
            node.get_metadata_str(mode=MetadataMode.EMBED),
        )
        for chunk in chunks:
            chunked_nodes.append(
                TextNode(
                    text=chunk,
                    metadata=dict(node.metadata),
                    excluded_embed_metadata_keys=list(node.excluded_embed_metadata_keys),
                    excluded_llm_metadata_keys=list(node.excluded_llm_metadata_keys),
                    metadata_template=node.metadata_template,
                    metadata_separator=node.metadata_separator,
                    text_template=node.text_template,
                )
            )

    return chunked_nodes


def main() -> None:
    # Prefer the project's .env values over any stale shell exports.
    load_dotenv(override=True)

    try:
        database_url = get_required_env("DATABASE_URL")
        get_required_env("OPENAI_API_KEY")
    except ValueError as exc:
        logger.error("%s", exc)
        raise SystemExit(1)

    configure_llamaindex(enable_llm=False)

    input_dir = os.environ.get("CRAWL_OUTPUT_DIR", DEFAULT_INPUT_DIR)
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error("Input directory %s does not exist. Run the crawl script first.", input_path)
        raise SystemExit(1)

    md_files = list(input_path.glob("*.md"))
    if not md_files:
        logger.error("No .md files found in %s. Run the crawl script first.", input_path)
        raise SystemExit(1)

    logger.info("Loading documents from %s (%d files)", input_path, len(md_files))
    documents = load_markdown_documents(input_path)

    logger.info("Loaded %d documents", len(documents))

    logger.info("Parsing markdown into nodes")
    parser = MarkdownNodeParser()
    markdown_nodes = parser.get_nodes_from_documents(documents)
    logger.info("Created %d markdown nodes", len(markdown_nodes))

    logger.info(
        "Splitting markdown nodes into embedding-safe chunks (size=%d, overlap=%d)",
        EMBED_CHUNK_SIZE,
        EMBED_CHUNK_OVERLAP,
    )
    nodes = chunk_nodes_for_embeddings(markdown_nodes)
    logger.info("Prepared %d embedding chunks", len(nodes))

    logger.info("Connecting to Supabase and creating index")
    storage_context = create_storage_context(database_url=database_url)

    index = VectorStoreIndex(nodes, storage_context=storage_context)

    logger.info("Indexing complete. Embeddings stored in Supabase collection '%s'", COLLECTION_NAME)


if __name__ == "__main__":
    main()
