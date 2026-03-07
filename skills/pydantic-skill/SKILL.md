---
name: pydantic-skill
description: Defines structured data models with Pydantic BaseModel. Use when defining LLM outputs or inputs for RAG, LlamaIndex structured outputs, or when the user mentions Pydantic, structured output, or response schemas.
---

# What are Pydantic models and when to use

Pydantic models group related fields into a single component. In RAG applications, they define **structured output**—the expected format the LLM returns (e.g., answer plus citations, confidence scores). They can also define **structured input** for tool calls or extraction pipelines.

## Pydantic models: name and collection of fields

Each field needs at minimum:
1. **Name** of the field
2. **Type** of data (e.g., `int`, `str`, `List[str]`)

## Nested models

Pydantic models can contain other models as fields:

```python
from typing import List
from pydantic import BaseModel, Field

class Song(BaseModel):
    """Data model for a song."""
    title: str
    length_seconds: int

class Album(BaseModel):
    """Data model for an album."""
    name: str
    artist: str
    songs: List[Song]
```

## Defining models for structured output (RAG / LlamaIndex)

1. **Name** the model (PascalCase)
2. **Docstring** describing what the model represents (helps the LLM)
3. **Fields** in the form `field_name: type`
4. **Optional**: `Field(..., description="...")` to guide the LLM on what to populate

```python
summary: str = Field(
    ..., description="A concise summary of this text chunk."
)
```

## Using with LlamaIndex

- **Query responses**: Use `llm.as_structured_llm(output_cls=YourModel)` and pass the structured LLM to `index.as_query_engine(llm=sllm)` so RAG queries return Pydantic objects.
- **Extraction**: Use `PydanticProgramExtractor` or `OpenAIPydanticProgram` for extracting structured data from documents.

## Additional Resources

- For usage examples, see [examples.md](examples.md)
- [Pydantic BaseModel documentation](https://docs.pydantic.dev/latest/api/base_model/)
- [LlamaIndex structured outputs](https://developers.llamaindex.ai/python/examples/structured_outputs/structured_outputs/)
