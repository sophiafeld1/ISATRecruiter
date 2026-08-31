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
import time
import uuid
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
    from database.db_write import _connect_from_kwargs, _db_connect_kwargs

    req_id = uuid.uuid4().hex[:8]
    logger.info("[%s] diagnostics: start", req_id)
    t0 = time.monotonic()

    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    db_kwargs = _db_connect_kwargs()

    result: dict = {
        "openai_key_set": bool(openai_key),
        "openai_key_length": len(openai_key),
        "openai_key_prefix_ok": openai_key.startswith("sk-"),
        "database_url_set": bool(database_url),
        "database_url_has_placeholders": "${{" in database_url,
        "pghost_set": bool(os.getenv("PGHOST")),
        "database_connection_mode": "dsn"
        if "dsn" in db_kwargs
        else "pghost"
        if os.getenv("PGHOST")
        else "db_host",
        "openai_test": None,
        "database_test": None,
    }

    if openai_key:
        try:
            from openai import OpenAI

            logger.info("[%s] diagnostics: testing OpenAI models.list", req_id)
            client = OpenAI(api_key=openai_key)
            client.models.list()
            result["openai_test"] = "ok"
            logger.info("[%s] diagnostics: testing OpenAI chat", req_id)
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say ok"}],
                max_tokens=5,
            )
            result["openai_chat_test"] = "ok"
            from langchain_openai import OpenAIEmbeddings

            logger.info("[%s] diagnostics: testing OpenAI embeddings", req_id)
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=openai_key,
            )
            embeddings.embed_query("test")
            result["openai_embed_test"] = "ok"
        except Exception as exc:
            logger.exception("[%s] diagnostics: OpenAI test failed", req_id)
            if result["openai_test"] == "ok":
                result["openai_chat_test"] = f"{type(exc).__name__}: {exc}"
                result["openai_test"] = f"models ok, chat failed: {type(exc).__name__}: {exc}"
            else:
                result["openai_test"] = f"{type(exc).__name__}: {exc}"
    else:
        result["openai_test"] = "skipped (OPENAI_API_KEY not set)"
        result["openai_chat_test"] = "skipped (OPENAI_API_KEY not set)"

    try:
        logger.info("[%s] diagnostics: testing database", req_id)
        conn = _connect_from_kwargs(db_kwargs)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
            result["chunks_with_embeddings"] = cur.fetchone()[0]
        conn.close()
        result["database_test"] = "ok"
        logger.info(
            "[%s] diagnostics: database ok chunks_with_embeddings=%s",
            req_id,
            result.get("chunks_with_embeddings"),
        )
    except Exception as exc:
        logger.exception("[%s] diagnostics: database test failed", req_id)
        if database_url or os.getenv("PGHOST") or os.getenv("DB_HOST"):
            result["database_test"] = f"{type(exc).__name__}: {exc}"
        else:
            result["database_test"] = "skipped (no database env vars set on this service)"

    try:
        logger.info("[%s] diagnostics: running chat smoke test", req_id)
        from LangGraph.main import process_question

        answer, _ = process_question("What is ISAT?", [])
        result["chat_smoke_test"] = "ok"
        result["chat_smoke_answer_len"] = len(answer or "")
        logger.info("[%s] diagnostics: chat smoke ok answer_len=%d", req_id, len(answer or ""))
    except Exception as exc:
        logger.exception("[%s] diagnostics: chat smoke failed", req_id)
        result["chat_smoke_test"] = f"{type(exc).__name__}: {exc}"

    logger.info("[%s] diagnostics: done in %.2fs", req_id, time.monotonic() - t0)
    return result


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    req_id = uuid.uuid4().hex[:8]
    logger.info(
        "[%s] chat: start question=%r history_len=%d",
        req_id,
        body.question[:120],
        len(body.conversation_history),
    )
    t0 = time.monotonic()
    try:
        # Import lazily so /health is ready quickly during Railway deploy checks.
        from LangGraph.main import process_question

        answer, history = process_question(body.question, body.conversation_history)
        logger.info(
            "[%s] chat: ok in %.2fs answer_len=%d",
            req_id,
            time.monotonic() - t0,
            len(answer or ""),
        )
        return ChatResponse(answer=answer, conversation_history=history)
    except Exception as exc:
        logger.error(
            "[%s] chat: failed after %.2fs\n%s",
            req_id,
            time.monotonic() - t0,
            traceback.format_exc(),
        )
        detail = f"{type(exc).__name__}: {exc}"
        raise HTTPException(status_code=500, detail=detail) from exc
