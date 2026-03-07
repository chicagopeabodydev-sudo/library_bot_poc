# llama-index-skill Examples

## Example 1 - Creating nodes from markdown using the MarkdownNodeParser
from llama_index.core.node_parser import MarkdownNodeParser

parser = MarkdownNodeParser()
nodes = parser.get_nodes_from_documents(markdown_docs)


## Example 2 - Load, index, store, and query steps using a "chromadb" open source vector store

import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext

# step 1 - load some documents
documents = SimpleDirectoryReader("./data").load_data()

# step 2 - initialize client, setting path to save data
db = chromadb.PersistentClient(path="./chroma_db")

# step 3 - create collection
chroma_collection = db.get_or_create_collection("quickstart")

# step 4 - assign chroma as the vector_store to the context
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# step 5 - create your index
index = VectorStoreIndex.from_documents(
    documents, storage_context=storage_context
)

# step 6 - create a query engine and query
query_engine = index.as_query_engine()
response = query_engine.query("What is the meaning of life?")
print(response)


## Example 3 - Querying using post-processing

from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor

# step 1 - build the index
index = VectorStoreIndex.from_documents(documents)

# step 2 - configure a retriever
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=10,
)

# step 3 - configure a response synthesizer
response_synthesizer = get_response_synthesizer()

# step 4 - assemble query engine
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    response_synthesizer=response_synthesizer,
    node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.7)],
)

# step 5 - execute the query
response = query_engine.query("What did the author do growing up?")
print(response)

