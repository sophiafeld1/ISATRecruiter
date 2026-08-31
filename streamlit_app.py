"""
ISAT RAG chat — Streamlit UI.

Config:
- **Local:** put `OPENAI_API_KEY`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and
  `DB_PASSWORD` in a `.env` file at the repo root (same as the rest of the project).
  `load_dotenv` runs before anything else needs them.
- **Streamlit Cloud:** add the same keys under **App settings → Secrets** (flat TOML
  is fine, e.g. `OPENAI_API_KEY = "sk-..."`). Those values override a `.env` in the
  repo if you accidentally committed placeholders.

Run: `streamlit run streamlit_app.py`
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_ROOT, ".env"))

import streamlit as st

st.set_page_config(
    page_title="ISAT Assistant",
    page_icon="🎓",
    layout="centered",
)

_secrets: dict[str, str] = {}
try:
    for _k in st.secrets:
        val = st.secrets[_k]
        if isinstance(val, dict):
            continue
        _secrets[str(_k)] = str(val)
except Exception:
    pass

# Streamlit Cloud: secrets from the dashboard must win over any `.env` shipped in the
# repo (placeholders). Locally, `.streamlit/secrets.toml` is usually absent — then only
# `load_dotenv` applies.
for _key in (
    "OPENAI_API_KEY",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
):
    if _key in _secrets:
        os.environ[_key] = _secrets[_key]

# Tutorial-style nested TOML: [openai]\napi_key = "sk-..."
try:
    _openai = st.secrets.get("openai")
    if isinstance(_openai, dict) and _openai.get("api_key"):
        os.environ["OPENAI_API_KEY"] = str(_openai["api_key"])
except Exception:
    pass

if not (os.environ.get("OPENAI_API_KEY") or "").strip():
    st.error(
        "Missing **OPENAI_API_KEY**. Add it to Streamlit **App settings → Secrets** "
        "as `OPENAI_API_KEY = \"sk-...\"`, or use a `.env` file when running locally."
    )
    st.stop()

from LangGraph.main import process_question


def _init_state() -> None:
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []


_init_state()

st.title("ISAT at JMU")
st.caption(
    "Ask about courses, concentrations, and the program. Uses your knowledge base and the model."
)

with st.sidebar:
    st.subheader("Session")
    if st.button("Clear conversation", type="secondary"):
        st.session_state.conversation_history = []
        st.rerun()

for msg in st.session_state.conversation_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Message…"):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                answer, st.session_state.conversation_history = process_question(
                    prompt,
                    st.session_state.conversation_history,
                )
            except Exception as e:
                answer = f"Something went wrong: {e}"
                st.session_state.conversation_history = (
                    st.session_state.conversation_history
                    + [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": answer},
                    ]
                )
        st.markdown(answer)
