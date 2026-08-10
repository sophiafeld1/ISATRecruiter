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
