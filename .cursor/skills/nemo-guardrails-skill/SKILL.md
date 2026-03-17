---
name: nemo-guardrails-skill
description: NeMo Guardrails is an open-source Python package for adding programmable guardrails around LLM calls. Use it to block unsafe, malicious, off-topic, or policy-violating user inputs, retrieved RAG content, tool usage, and model responses.
---

# When to use this skill
Use this skill when an LLM-based application needs safety or policy checks before or after model calls.

This is especially relevant for this project because the chatbot flow is:

1. A user submits a question in Streamlit.
2. Input rails verify that the question is safe and on topic.
3. The application retrieves relevant content from the RAG index.
4. Retrieval rails optionally validate or filter the retrieved content.
5. The LLM generates an answer using the approved context.
6. Output rails verify the answer before it is shown in Streamlit.

Use NeMo Guardrails when implementing or improving any of the following:

1. Input rails for blocked terms, jailbreak attempts, unsafe requests, or off-topic questions.
2. Retrieval rails for validating RAG content before it is sent to the LLM.
3. Dialog rails for controlling allowed conversation flows.
4. Execution rails for validating tool or action usage.
5. Output rails for filtering unsafe or policy-violating responses.

## Key steps

1. Create guardrail configuration files, usually in a dedicated config directory.
2. Load the configuration with `RailsConfig.from_path(...)` or `RailsConfig.from_content(...)`.
3. Create an `LLMRails` instance from the loaded config.
4. Pass chat messages to `rails.generate(...)` or `rails.generate_async(...)`.
5. Handle blocked results in application code and return a safe fallback message to the user.

## Project-specific guidance

For this repository, prefer a flow like this:

1. Accept the question in Streamlit.
2. Run input rails before retrieval.
3. If the input passes, retrieve candidate context from the vector store.
4. Run retrieval checks if you need to filter or validate the retrieved content.
5. Generate the final answer.
6. Run output rails on the answer.
7. Return either the approved answer or a safe failure message to Streamlit.

Keep the rails logic separate from the UI logic so the same checks can also be reused from CLI scripts or tests.

## Checklist before implementation

- [ ] Main LLM provider and credentials are available.
- [ ] The app has a clear definition of what counts as on-topic for the crawled website content.
- [ ] Guardrail configuration files have a stable home, such as `guardrails/` or `config/guardrails/`.
- [ ] The application has user-friendly fallback messages for blocked input and blocked output.
- [ ] Optional custom actions are identified if built-in rails are not enough.

## RAG and knowledge base notes

When using NeMo Guardrails with RAG:

- Prepare knowledge base documents in markdown format when using documentation-backed rails.
- Keep RAG documents organized in a predictable folder such as `kb/`.
- Use retrieval rails when you need to validate or filter retrieved chunks before they reach the LLM.
- Treat retrieval validation as separate from input validation. A safe question can still retrieve content that needs additional checks.

## Custom actions with `actions.py`

Custom actions are useful when project-specific validation is needed. Define them in `actions.py` with the `@action` decorator.

Example:

```python
from typing import Optional

from nemoguardrails.actions import action


@action(is_system_action=True)
async def check_blocked_terms(context: Optional[dict] = None) -> bool:
    """Return True when a blocked term is present in the bot response."""
    context = context or {}
    bot_response = context.get("bot_message", "")
    blocked_terms = ["confidential", "proprietary", "secret"]

    return any(term in bot_response.lower() for term in blocked_terms)
```

## Additional Resources

- For usage examples, see [examples.md](examples.md)
- [NeMo Guardrails documentation](https://docs.nvidia.com/nemo/guardrails/latest/index.html)
- [Guardrail types](https://docs.nvidia.com/nemo/guardrails/latest/about/rail-types.html)
- [Installation guide](https://docs.nvidia.com/nemo/guardrails/latest/getting-started/installation-guide.html)
- [Python API overview](https://docs.nvidia.com/nemo/guardrails/latest/run-rails/using-python-apis/overview.html)