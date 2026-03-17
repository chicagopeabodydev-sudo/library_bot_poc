#!/usr/bin/env python3
"""
Load markdown from website-markdown/, index with LlamaIndex, and store in Supabase pgvector.

Reads configuration from environment variables:
  DATABASE_URL     - PostgreSQL connection string for Supabase (required)
  OPENAI_API_KEY   - Used for embeddings (required)
  CRAWL_OUTPUT_DIR - Input directory for markdown files (default: website-markdown)
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import MetadataMode, TextNode

# Ensure project root is on path so we can import sibling script modules.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.rag import COLLECTION_NAME, configure_llamaindex, create_storage_context, get_required_env

DEFAULT_INPUT_DIR = "website-markdown"
EMBED_CHUNK_SIZE = 1024
EMBED_CHUNK_OVERLAP = 100

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    documents = SimpleDirectoryReader(
        input_dir=str(input_path),
        required_exts=[".md"],
    ).load_data()

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
