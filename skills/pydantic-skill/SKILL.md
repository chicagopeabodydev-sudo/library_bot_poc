---
name: pydantic-skill
description: Pydantic models are simply classes which inherit from BaseModel and define fields as annotated attributes.
---

# What are Pydantic models and when to use
Pydantic models are helpful to group multiple related fields into a single component. For example, with a RAG application they can be used to support a "structured output" where the Pydantic model defines the expected data format the LLM should return.


## Pydantic models are essentially a name and collection of fields
### each fields needs 2 things at a minimum:
- 1. name of the field
- 2. type of data it stores, for example "int" (integer) and "str" (string)

## Pydantic models can be fields of other models
### Example: the Album model below has a "songs" field that's a list of Song models (defined above it)
    - python:
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

## defining Pydantic models for structure-data output sets:
    - 1. Name of the model (capitalized)
    - 2. python docstring that defines the type of thing being modeled (useful for the LLM)
    - 3. fields - at a minimum this needs a name and datatype in this format: [field-name]: [type]
    - 4. optionally, a Field(..., description= "[description-here]") can be added that describes the kind of data that should be stored by the field
        - python example:
            summary: str = Field(
                ..., description="A concise summary of this text chunk."
            )


## Additional Resources
- For usage examples, see [examples.md](examples.md)
- BaseModel documentation [BaseModel](https://docs.pydantic.dev/latest/api/base_model/)
- LlamaIndex structured output with Pydantic models documentation [LlamaIndex-Structured_Output](https://developers.llamaindex.ai/python/examples/structured_outputs/structured_outputs/)
