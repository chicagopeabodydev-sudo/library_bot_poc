# pydantic-skill Examples

Examples for using Pydantic models with LlamaIndex for RAG structured outputs.

---

## Example 1 - Define a Pydantic model for extraction

Use `Field(..., description="...")` to describe each field for the LLM.

```python
from pydantic import BaseModel, Field
from typing import List

class NodeMetadata(BaseModel):
    """Node metadata."""

    entities: List[str] = Field(
        ..., description="Unique entities in this text chunk."
    )
    summary: str = Field(
        ..., description="A concise summary of this text chunk."
    )
    contains_number: bool = Field(
        ...,
        description="Whether the text chunk contains any numbers (ints, floats, etc.)",
    )
```

---

## Example 2 - Use Pydantic with PydanticProgramExtractor

Extract structured data from nodes using `PydanticProgramExtractor` and `OpenAIPydanticProgram`.

```python
from llama_index.program.openai import OpenAIPydanticProgram
from llama_index.core.extractors import PydanticProgramExtractor

openai_program = OpenAIPydanticProgram.from_defaults(
    output_cls=NodeMetadata,
    prompt_template_str="{input}",
)

program_extractor = PydanticProgramExtractor(
    program=openai_program, input_key="input", show_progress=True
)

sample_entry = program_extractor.extract(orig_nodes[0:1])[0]
```

---

## Example 3 - Structured RAG output with as_structured_llm

Define an output model and use it with the query engine so RAG responses return Pydantic objects.

**Step 1 – Define the output model**

```python
from pydantic import BaseModel, Field
from typing import List

class RAGOutput(BaseModel):
    """Output containing the response, page numbers, and confidence."""

    response: str = Field(..., description="The answer to the question.")
    page_numbers: List[int] = Field(
        ...,
        description="Page numbers of sources used. Omit if context is irrelevant.",
    )
    confidence: float = Field(
        ...,
        description="Confidence value between 0-1 for the correctness of the result.",
    )
    confidence_explanation: str = Field(
        ..., description="Explanation for the confidence score."
    )
```

**Step 2 – Create structured LLM and query engine**

```python
from llama_index.core import VectorStoreIndex
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker

# Assume index and llm already exist
index = VectorStoreIndex.from_documents(docs)

reranker = FlagEmbeddingReranker(
    top_n=5,
    model="BAAI/bge-reranker-large",
)

sllm = llm.as_structured_llm(output_cls=RAGOutput)

query_engine = index.as_query_engine(
    similarity_top_k=5,
    node_postprocessors=[reranker],
    llm=sllm,
    response_mode="tree_summarize",
)

response = query_engine.query("Net sales for each product category in 2021?")
print(response)  # response is a RAGOutput instance
```
