# nemo-guardrails-skill Examples

These examples focus on the project goal for this repository: a Streamlit chatbot that uses RAG and applies NeMo Guardrails before and after the LLM call.

---

## Example 1 - Load guardrail configuration from a path

Use this when your guardrail config lives in a folder such as `guardrails/` or `config/guardrails/`.

```python
from nemoguardrails import LLMRails, RailsConfig

config = RailsConfig.from_path("guardrails")
rails = LLMRails(config)
```

Expected directory structure:

```text
guardrails/
├── config.yml
├── rails/
│   ├── input.co
│   ├── output.co
│   └── ...
├── kb/
│   └── site-docs.md
├── actions.py
└── config.py
```

---

## Example 2 - Guardrail a user question before retrieval

This is the simplest project-relevant pattern: validate the question before doing RAG retrieval.

```python
from nemoguardrails import LLMRails, RailsConfig

config = RailsConfig.from_path("guardrails")
rails = LLMRails(config)

messages = [
    {
        "role": "user",
        "content": "What are the library's weekend hours?",
    }
]

response = rails.generate(messages=messages)
print(response["content"])
```

If the user asks something unsafe or off topic, your application code should catch that result and return a safe fallback message instead of continuing to retrieval.

---

## Example 3 - End-to-end RAG flow with input and output rails

This example mirrors the architecture described in the project overview.

```python
from nemoguardrails import LLMRails, RailsConfig


def retrieve_context(question: str) -> str:
    # Replace this stub with the project's LlamaIndex + Supabase retrieval code.
    return "Library hours: Monday to Saturday, 9 AM to 6 PM."


def answer_question(question: str) -> str:
    config = RailsConfig.from_path("guardrails")
    rails = LLMRails(config)

    # Step 1: input rails
    input_result = rails.generate(messages=[{"role": "user", "content": question}])
    approved_question = input_result["content"]

    # Step 2: retrieval
    context = retrieve_context(approved_question)

    # Step 3: final answer generation using approved context
    answer_result = rails.generate(
        messages=[
            {"role": "context", "content": {"retrieved_context": context}},
            {"role": "user", "content": approved_question},
        ]
    )

    # Step 4: output rails are applied by the configured rails
    return answer_result["content"]


print(answer_question("What are the library's weekend hours?"))
```

In a Streamlit app, wrap this flow so blocked input or blocked output produces a user-friendly error message.

---

## Example 4 - Build a config from strings for tests

This is useful for unit tests or quick experiments.

```python
from nemoguardrails import LLMRails, RailsConfig

yaml_content = """
models:
  - type: main
    engine: openai
    model: gpt-4o-mini

instructions:
  - type: general
    content: |
      You are a library assistant. Answer only with safe, concise responses.
"""

colang_content = """
define user ask about library
  "What are the library hours?"
  "Where is the circulation desk?"

define flow
  user ask about library
  bot express greeting
"""

config = RailsConfig.from_content(
    yaml_content=yaml_content,
    colang_content=colang_content,
)
rails = LLMRails(config)
```

---

## Example 5 - Use conversation history

Use message history when the chatbot needs multi-turn context.

```python
from nemoguardrails import LLMRails, RailsConfig

config = RailsConfig.from_path("guardrails")
rails = LLMRails(config)

messages = [
    {"role": "user", "content": "My favorite branch is downtown."},
    {"role": "assistant", "content": "Got it. I can answer questions about the downtown branch."},
    {"role": "user", "content": "What time does it close on Friday?"},
]

response = rails.generate(messages=messages)
print(response["content"])
```

---

## Example 6 - Pass structured context into a custom action

Use context when a rail or custom action needs application state.

```python
from typing import Optional

from nemoguardrails.actions import action


@action()
async def check_permissions(context: Optional[dict] = None) -> bool:
    context = context or {}
    user_role = context.get("user_role")
    return user_role == "admin"
```

Then pass context when generating:

```python
from nemoguardrails import LLMRails, RailsConfig

config = RailsConfig.from_path("guardrails")
rails = LLMRails(config)

response = rails.generate(
    messages=[
        {
            "role": "context",
            "content": {
                "user_name": "Alice",
                "user_role": "admin",
            },
        },
        {"role": "user", "content": "What permissions do I have?"},
    ]
)

print(response["content"])
```

---

## Example 7 - Define a project-specific custom action

This kind of action is useful for blocking spam, phishing language, or other project rules.

```python
from typing import Optional

from nemoguardrails.actions import action


@action()
async def check_custom_policy(context: Optional[dict] = None) -> bool:
    """Return True when the message passes the custom policy."""
    context = context or {}
    user_message = context.get("last_user_message", "")
    forbidden_words = ["spam", "phishing"]

    return not any(word in user_message.lower() for word in forbidden_words)


@action(name="fetch_user_data")
async def get_user_info(user_id: str) -> dict:
    """Fetch user data from an external service."""
    return {"user_id": user_id, "status": "active"}
```

---

## Example 8 - Handle blocked input or output in Streamlit

This snippet shows the application behavior you want even if the exact blocked-response shape varies by config.

```python
import streamlit as st


def safe_answer(question: str) -> str:
    try:
        return answer_question(question)
    except Exception:
        # Replace broad exception handling with project-specific guardrail handling.
        return "Sorry, I can't help with that request."


question = st.chat_input("Ask about the library website")
if question:
    st.chat_message("user").write(question)
    answer = safe_answer(question)
    st.chat_message("assistant").write(answer)
```

Use this pattern so the UI always returns a safe, clear message when guardrails block either the input or the output.
