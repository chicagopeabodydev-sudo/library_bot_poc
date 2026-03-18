from __future__ import annotations

from typing import Any, Optional

try:
    from nemoguardrails.actions import action  # pyright: ignore[reportMissingImports]
except ImportError:
    # Keep this module importable before optional guardrails deps are installed.
    def action(*args: Any, **kwargs: Any):
        def decorator(func: Any) -> Any:
            return func

        return decorator

INPUT_BLOCKED_TERMS = {
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal the system prompt",
    "show the hidden prompt",
    "bypass guardrails",
    "jailbreak",
    "sudo",
    "rm -rf",
}

OUTPUT_BLOCKED_TERMS = {
    "api key",
    "password",
    "secret",
    "confidential",
    "social security number",
}

LIBRARY_TOPIC_HINTS = {
    "library",
    "hours",
    "branch",
    "catalog",
    "borrow",
    "borrowing",
    "checkout",
    "book",
    "books",
    "event",
    "events",
    "card",
    "account",
    "contact",
    "location",
    "locations",
    "program",
    "services",
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return " ".join(_normalize_text(v) for v in value.values()).strip()
    if isinstance(value, (list, tuple, set)):
        return " ".join(_normalize_text(v) for v in value).strip()
    return str(value).strip()


def _read_context_text(context: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = context.get(key)
        text = _normalize_text(value)
        if text:
            return text
    return ""


@action(name="CheckLibraryInputAction", is_system_action=True)
async def check_library_input(context: Optional[dict] = None) -> bool:
    """Block empty questions and obvious prompt-injection attempts."""
    context = context or {}
    user_text = _read_context_text(
        context,
        ["last_user_message", "user_message", "user_input"],
    ).lower()

    if not user_text:
        return False

    return not any(term in user_text for term in INPUT_BLOCKED_TERMS)


@action(name="CheckLibraryOutputAction", is_system_action=True)
async def check_library_output(context: Optional[dict] = None) -> bool:
    """Block obvious secret leakage or sensitive output terms."""
    context = context or {}
    bot_text = _read_context_text(
        context,
        ["bot_message", "bot_response", "response"],
    ).lower()

    if not bot_text:
        return False

    return not any(term in bot_text for term in OUTPUT_BLOCKED_TERMS)


@action(name="CheckRetrievedContextAction", is_system_action=True)
async def check_retrieved_context(context: Optional[dict] = None) -> bool:
    """Require non-empty retrieved context with basic library-topic signals."""
    context = context or {}
    retrieved_text = _read_context_text(
        context,
        ["retrieved_context", "relevant_chunks", "context"],
    ).lower()

    if not retrieved_text:
        return False

    return any(term in retrieved_text for term in LIBRARY_TOPIC_HINTS)
