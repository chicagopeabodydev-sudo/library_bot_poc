#!/usr/bin/env python3
"""Streamlit UI for querying the indexed library content."""

from __future__ import annotations

from typing import Any

import streamlit as st
from dotenv import load_dotenv

from scripts.query import build_query_engine, extract_sources, run_query
from scripts.rag import COLLECTION_NAME, get_required_env

APP_TITLE = "Library Bot"
APP_CAPTION = "Ask questions about the indexed website content."
SOURCE_EXPANDER_LABEL = "Retrieved sources"

st.set_page_config(page_title=APP_TITLE)


def render_sources(sources: list[dict[str, Any]]) -> None:
    """Render retrieved source snippets below an answer."""
    if not sources:
        return

    with st.expander(SOURCE_EXPANDER_LABEL):
        for index, source in enumerate(sources, start=1):
            label = source.get("label", f"Source {index}")
            score = source.get("score")
            metadata = source.get("metadata", {})
            excerpt = source.get("excerpt", "")

            heading = f"{index}. {label}"
            if isinstance(score, (int, float)):
                heading = f"{heading} (score: {score:.3f})"

            st.markdown(f"**{heading}**")

            file_path = metadata.get("file_path") or metadata.get("source")
            url = metadata.get("url")
            if file_path:
                st.caption(str(file_path))
            elif url:
                st.caption(str(url))

            st.write(excerpt or "No excerpt available.")


@st.cache_resource(show_spinner=False)
def get_cached_query_engine() -> Any:
    """Build the shared query engine once per Streamlit session."""
    database_url = get_required_env("DATABASE_URL")
    return build_query_engine(database_url=database_url)


def main() -> None:
    """Render the Streamlit RAG chat UI."""
    load_dotenv(override=True)

    st.title(APP_TITLE)
    st.caption(APP_CAPTION)

    with st.sidebar:
        st.write(f"Collection: `{COLLECTION_NAME}`")
        st.write("Configuration is read from `.env`.")
        st.write("Use `QUERY_TEXT` only as the CLI fallback for `python scripts/query.py`.")

    try:
        query_engine = get_cached_query_engine()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Unable to load the query engine: {exc}")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Ask a question about the indexed library content.",
                "sources": [],
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            render_sources(message.get("sources", []))

    if prompt := st.chat_input("Ask about the indexed content"):
        st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching the library index..."):
                try:
                    response = run_query(prompt, query_engine=query_engine)
                except ValueError as exc:
                    st.error(str(exc))
                    return
                except Exception as exc:
                    st.error(f"Query failed: {exc}")
                    return

            answer_text = str(response)
            sources = extract_sources(response)

            st.write(answer_text)
            render_sources(sources)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer_text,
                "sources": sources,
            }
        )


if __name__ == "__main__":
    main()
