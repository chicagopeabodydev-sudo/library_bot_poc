"""Unit tests for query helpers and the CLI fallback."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from scripts import query


@dataclass
class FakeResponse:
    text: str
    source_nodes: list[str]

    def __str__(self) -> str:
        return self.text


class FakeQueryEngine:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.queries: list[str] = []

    def query(self, query_text: str) -> FakeResponse:
        self.queries.append(query_text)
        return self.response


class FakeIndex:
    def __init__(self, engine: FakeQueryEngine) -> None:
        self.engine = engine
        self.similarity_top_k: int | None = None

    def as_query_engine(self, *, similarity_top_k: int) -> FakeQueryEngine:
        self.similarity_top_k = similarity_top_k
        return self.engine


def test_build_query_engine_configures_models_and_returns_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build a reusable query engine for CLI and UI callers."""
    configure_calls: list[bool] = []
    monkeypatch.setattr(
        query,
        "configure_llamaindex",
        lambda *, enable_llm: configure_calls.append(enable_llm),
    )

    response = FakeResponse(text="Answer", source_nodes=[])
    engine = FakeQueryEngine(response=response)
    index = FakeIndex(engine=engine)
    database_urls: list[str] = []
    monkeypatch.setattr(
        query,
        "load_vector_index",
        lambda *, database_url: database_urls.append(database_url) or index,
    )

    built_engine = query.build_query_engine(database_url="postgresql://example")

    assert configure_calls == [True]
    assert database_urls == ["postgresql://example"]
    assert built_engine is engine
    assert index.similarity_top_k == query.SIMILARITY_TOP_K


def test_run_query_uses_supplied_engine() -> None:
    """Avoid rebuilding the backend when an engine is already available."""
    response = FakeResponse(text="Answer", source_nodes=[])
    engine = FakeQueryEngine(response=response)

    result = query.run_query("  What are the library hours?  ", query_engine=engine)

    assert result is response
    assert engine.queries == ["What are the library hours?"]


def test_extract_sources_returns_metadata_and_excerpt() -> None:
    """Convert source nodes into UI-friendly dictionaries."""
    source_node = type(
        "FakeSourceNode",
        (),
        {
            "score": 0.9,
            "node": type(
                "FakeNode",
                (),
                {
                    "metadata": {"file_name": "hours.md", "url": "https://example.com/hours"},
                    "get_content": lambda self: "Library hours are Monday through Friday." * 20,
                },
            )(),
        },
    )()
    response = type("FakeResponseObject", (), {"source_nodes": [source_node]})()

    sources = query.extract_sources(response, max_excerpt_chars=60)

    assert len(sources) == 1
    assert sources[0]["label"] == "hours.md"
    assert sources[0]["score"] == 0.9
    assert sources[0]["metadata"]["url"] == "https://example.com/hours"
    assert sources[0]["excerpt"].endswith("...")


def test_query_requires_query_text(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Exit with an error when QUERY_TEXT is missing."""
    monkeypatch.setattr(query, "load_dotenv", lambda override=True: None)

    def fake_get_required_env(name: str) -> str:
        if name == "QUERY_TEXT":
            raise ValueError("QUERY_TEXT environment variable is required")
        return "configured"

    monkeypatch.setattr(query, "get_required_env", fake_get_required_env)
    monkeypatch.setattr(query, "configure_llamaindex", lambda *, enable_llm: None)

    with pytest.raises(SystemExit):
        query.main()

    assert "QUERY_TEXT environment variable is required" in caplog.text


def test_query_runs_and_prints_response(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use QUERY_TEXT as the CLI fallback and print the response text."""
    monkeypatch.setattr(query, "load_dotenv", lambda override=True: None)

    values = {
        "DATABASE_URL": "postgresql://example",
        "QUERY_TEXT": "What are the library hours?",
    }
    monkeypatch.setattr(query, "get_required_env", lambda name: values[name])

    response = FakeResponse(text="The library is open until 9 PM.", source_nodes=["node-a"])
    run_query_calls: list[tuple[str, str, int]] = []
    monkeypatch.setattr(
        query,
        "run_query",
        lambda query_text, *, database_url, similarity_top_k: run_query_calls.append(
            (query_text, database_url, similarity_top_k)
        )
        or response,
    )

    query.main()

    assert run_query_calls == [
        ("What are the library hours?", "postgresql://example", query.SIMILARITY_TOP_K)
    ]
    assert capsys.readouterr().out.strip() == "The library is open until 9 PM."
