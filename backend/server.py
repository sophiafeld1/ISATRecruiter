"""
HTTP API for the LangGraph chat workflow.

Deploy this service (Railway, Render, etc.) and point the Next.js app at it via
BACKEND_URL. Vercel cannot run the local Python subprocess used in dev.
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="ISAT Recruiter API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    conversation_history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    conversation_history: list[dict]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/diagnostics")
def diagnostics() -> dict:
    """Check runtime config on Railway without exposing secrets."""
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    database_url = (os.getenv("DATABASE_URL") or "").strip()

    result: dict = {
        "openai_key_set": bool(openai_key),
        "openai_key_length": len(openai_key),
        "openai_key_prefix_ok": openai_key.startswith("sk-"),
        "database_url_set": bool(database_url),
        "database_url_has_placeholders": "${{" in database_url,
        "openai_test": None,
        "database_test": None,
    }

    if openai_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_key)
            client.models.list()
            result["openai_test"] = "ok"
        except Exception as exc:
            result["openai_test"] = f"{type(exc).__name__}: {exc}"
    else:
        result["openai_test"] = "skipped (OPENAI_API_KEY not set)"

    if database_url and "${{" not in database_url:
        try:
            import psycopg2

            conn = psycopg2.connect(database_url)
            conn.close()
            result["database_test"] = "ok"
        except Exception as exc:
            result["database_test"] = f"{type(exc).__name__}: {exc}"
    else:
        result["database_test"] = "skipped (DATABASE_URL missing or unresolved)"

    return result


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    try:
        # Import lazily so /health is ready quickly during Railway deploy checks.
        from LangGraph.main import process_question

        answer, history = process_question(body.question, body.conversation_history)
        return ChatResponse(answer=answer, conversation_history=history)
    except Exception as exc:
        logger.error("Chat request failed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc)) from exc
