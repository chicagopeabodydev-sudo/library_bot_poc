#!/usr/bin/env python3
"""Shared NeMo Guardrails orchestration for the RAG query flow."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import sys
from typing import Any

try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False

from nemoguardrails import LLMRails, RailsConfig  # pyright: ignore[reportMissingImports]
from nemoguardrails.rails.llm.options import RailStatus, RailType, RailsResult  # pyright: ignore[reportMissingImports]

# Ensure project root is on path so we can import sibling modules/packages.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from guardrails.actions import LIBRARY_TOPIC_HINTS
from scripts import query

DEFAULT_GUARDRAILS_DIR = "guardrails"
DEFAULT_BLOCKED_INPUT_MESSAGE = "Sorry, I can only help with safe questions about the indexed library website."
DEFAULT_NO_APPROVED_CONTEXT_MESSAGE = "Sorry, I couldn't find approved source material to answer that safely."
DEFAULT_BLOCKED_OUTPUT_MESSAGE = "Sorry, I can't provide that response."


@dataclass
class GuardrailedQueryResult:
    """Structured result for a guardrailed query pipeline run."""

    approved_question: str | None
    answer_text: str
    blocked: bool
    block_stage: str | None
    source_nodes: list[Any]
    sources: list[dict[str, Any]]
    rail_name: str | None = None


def _is_guardrails_enabled() -> bool:
    value = os.environ.get("GUARDRAILS_ENABLED", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _guardrails_config_dir(config_dir: str | None = None) -> str:
    configured = config_dir or os.environ.get("GUARDRAILS_CONFIG_DIR", DEFAULT_GUARDRAILS_DIR)
    return str(Path(configured).resolve())


@lru_cache(maxsize=4)
def load_guardrails_app(config_dir: str | None = None) -> LLMRails:
    """Load and cache the shared NeMo Guardrails application."""
    resolved_dir = _guardrails_config_dir(config_dir)
    config = RailsConfig.from_path(resolved_dir)
    return LLMRails(config)


def apply_input_guardrails(question: str, *, config_dir: str | None = None) -> RailsResult:
    """Run input rails against the raw user question."""
    normalized_question = query.normalize_query_text(question)
    rails = load_guardrails_app(config_dir)
    return rails.check(
        [{"role": "user", "content": normalized_question}],
        rail_types=[RailType.INPUT],
    )


def apply_output_guardrails(
    question: str,
    answer_text: str,
    *,
    config_dir: str | None = None,
) -> RailsResult:
    """Run output rails against a synthesized bot response."""
    normalized_question = query.normalize_query_text(question)
    rails = load_guardrails_app(config_dir)
    return rails.check(
        [
            {"role": "user", "content": normalized_question},
            {"role": "assistant", "content": answer_text},
        ],
        rail_types=[RailType.OUTPUT],
    )


def _node_text(source_node: Any) -> str:
    node = getattr(source_node, "node", source_node)
    try:
        return str(node.get_content()).strip()
    except (AttributeError, TypeError):
        return str(getattr(node, "text", "")).strip()


def _node_metadata(source_node: Any) -> dict[str, Any]:
    node = getattr(source_node, "node", source_node)
    return dict(getattr(node, "metadata", {}) or {})


def _node_has_library_signals(source_node: Any) -> bool:
    text = _node_text(source_node).lower()
    metadata = _node_metadata(source_node)
    metadata_blob = " ".join(str(value).lower() for value in metadata.values())

    if not text:
        return False

    for hint in LIBRARY_TOPIC_HINTS:
        if hint in text or hint in metadata_blob:
            return True

    # If a retrieved node has normal source metadata and substantial text,
    # keep it unless it is clearly empty or malformed.
    return bool(text and (metadata.get("file_name") or metadata.get("source") or metadata.get("url")))


def filter_retrieved_nodes(nodes: list[Any]) -> list[Any]:
    """Remove empty or clearly off-topic retrieved nodes before synthesis."""
    return [node for node in nodes if _node_has_library_signals(node)]


def _extract_sources_from_nodes(nodes: list[Any]) -> list[dict[str, Any]]:
    response_like = type("RetrievedNodesResponse", (), {"source_nodes": nodes})()
    return query.extract_sources(response_like)


def run_guardrailed_query(
    query_text: str,
    *,
    query_pipeline: query.QueryPipeline | Any | None = None,
    database_url: str | None = None,
    similarity_top_k: int = query.SIMILARITY_TOP_K,
    config_dir: str | None = None,
) -> GuardrailedQueryResult:
    """Run the shared query flow with input, retrieval, and output guardrails."""
    load_dotenv(override=True)
    normalized_query = query.normalize_query_text(query_text)

    if _is_guardrails_enabled():
        input_result = apply_input_guardrails(normalized_query, config_dir=config_dir)
        if input_result.status == RailStatus.BLOCKED:
            return GuardrailedQueryResult(
                approved_question=None,
                answer_text=DEFAULT_BLOCKED_INPUT_MESSAGE,
                blocked=True,
                block_stage="input",
                source_nodes=[],
                sources=[],
                rail_name=input_result.rail,
            )

        approved_question = input_result.content or normalized_query
    else:
        approved_question = normalized_query

    pipeline = query_pipeline or query.build_query_engine(
        database_url=database_url,
        similarity_top_k=similarity_top_k,
    )

    retrieved_nodes = query.retrieve_nodes(
        approved_question,
        retriever=pipeline.retriever if hasattr(pipeline, "retriever") else None,
        database_url=None if hasattr(pipeline, "retriever") else database_url,
        similarity_top_k=similarity_top_k,
    )
    approved_nodes = filter_retrieved_nodes(retrieved_nodes)

    if not approved_nodes:
        return GuardrailedQueryResult(
            approved_question=approved_question,
            answer_text=DEFAULT_NO_APPROVED_CONTEXT_MESSAGE,
            blocked=True,
            block_stage="retrieval",
            source_nodes=[],
            sources=[],
        )

    response = query.synthesize_response(
        approved_question,
        approved_nodes,
        response_synthesizer=pipeline.response_synthesizer if hasattr(pipeline, "response_synthesizer") else None,
    )
    answer_text = str(response)

    if _is_guardrails_enabled():
        output_result = apply_output_guardrails(
            approved_question,
            answer_text,
            config_dir=config_dir,
        )
        if output_result.status == RailStatus.BLOCKED:
            return GuardrailedQueryResult(
                approved_question=approved_question,
                answer_text=DEFAULT_BLOCKED_OUTPUT_MESSAGE,
                blocked=True,
                block_stage="output",
                source_nodes=[],
                sources=[],
                rail_name=output_result.rail,
            )
        final_answer = output_result.content
    else:
        final_answer = answer_text

    return GuardrailedQueryResult(
        approved_question=approved_question,
        answer_text=final_answer,
        blocked=False,
        block_stage=None,
        source_nodes=approved_nodes,
        sources=_extract_sources_from_nodes(approved_nodes),
    )
