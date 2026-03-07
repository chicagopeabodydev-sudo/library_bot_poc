# pydantic-skill Examples

## Example 1 - defining Pydantic models to use with llama-index's structured-output

# step 1 - define the Pydantoic model
# NOTE - each fields includes sytax to describe its type of data using: =Field(..., description="desc-here")

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
        description=(
            "Whether the text chunk contains any numbers (ints, floats, etc.)"
        ),
    )

# step 2 - set the "output_cls" to the structured-output NodeMetadata defined above

from llama_index.program.openai import OpenAIPydanticProgram
from llama_index.core.extractors import PydanticProgramExtractor

openai_program = OpenAIPydanticProgram.from_defaults(
    output_cls=NodeMetadata,
    prompt_template_str="{input}",
    # extract_template_str=EXTRACT_TEMPLATE_STR
)

program_extractor = PydanticProgramExtractor(
    program=openai_program, input_key="input", show_progress=True
)

# step 3 - extract the data using the PydanticProgramExtractor and output the results

sample_entry = program_extractor.extract(orig_nodes[0:1])[0]
display(sample_entry)


## Example 2 - using Pydantic models to define structured-data output with llama-index vector store
- step 1 - get an index
from llama_index.core import VectorStoreIndex

# skip chunking since we're doing page-level chunking
index = VectorStoreIndex(docs)

- step 2 - (optional) configure re-ranking
from llama_index.postprocessor.flag_embedding_reranker import (
    FlagEmbeddingReranker,
)

reranker = FlagEmbeddingReranker(
    top_n=5,
    model="BAAI/bge-reranker-large",
)

- step 3 - define the "Output" Pydantic model and use it with ".as_structured_llm(output_cls=[model-name-here])"
from pydantic import BaseModel, Field
from typing import List

class Output(BaseModel):
    """Output containing the response, page numbers, and confidence."""

    response: str = Field(..., description="The answer to the question.")
    page_numbers: List[int] = Field(
        ...,
        description="The page numbers of the sources used to answer this question. Do not include a page number if the context is irrelevant.",
    )
    confidence: float = Field(
        ...,
        description="Confidence value between 0-1 of the correctness of the result.",
    )
    confidence_explanation: str = Field(
        ..., description="Explanation for the confidence score"
    )


sllm = llm.as_structured_llm(output_cls=Output)

- step 4 - run a query using the "structured LLM" (sllm) and the re-ranker defined above
query_engine = index.as_query_engine(
    similarity_top_k=5,
    node_postprocessors=[reranker],
    llm=sllm,
    response_mode="tree_summarize",  # you can also select other modes like `compact`, `refine`
)

response = query_engine.query("Net sales for each product category in 2021")
print(str(response))

