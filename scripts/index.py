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
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.vector_stores.supabase import SupabaseVectorStore

DEFAULT_INPUT_DIR = "website-markdown"
COLLECTION_NAME = "website_docs"
EMBEDDING_DIMENSION = 1536  # OpenAI text-embedding-3-small

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        raise SystemExit(1)

    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable is required")
        raise SystemExit(1)

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
    nodes = parser.get_nodes_from_documents(documents)
    logger.info("Created %d nodes", len(nodes))

    logger.info("Connecting to Supabase and creating index")
    vector_store = SupabaseVectorStore(
        postgres_connection_string=database_url,
        collection_name=COLLECTION_NAME,
        dimension=EMBEDDING_DIMENSION,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex(nodes, storage_context=storage_context)

    logger.info("Indexing complete. Embeddings stored in Supabase collection '%s'", COLLECTION_NAME)


if __name__ == "__main__":
    main()
