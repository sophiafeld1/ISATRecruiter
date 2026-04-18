"""
ISAT RAG chat — Streamlit UI.

Local:   streamlit run streamlit_app.py
Deploy: https://share.streamlit.io — set Main file to streamlit_app.py, add secrets
        (OPENAI_API_KEY, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD) for a
        reachable Postgres instance (e.g. Neon, Supabase).
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
        _secrets[str(_k)] = str(st.secrets[_k])
except Exception:
    pass
for _key in (
    "OPENAI_API_KEY",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
):
    if _key in _secrets:
        os.environ[_key] = str(_secrets[_key])

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
