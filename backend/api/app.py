"""
FastAPI application for the Stock Analyst Agent.

Endpoints:
  POST /api/analyze          — main chat + analysis endpoint
  GET  /api/session/{id}     — fetch session memory
  DELETE /api/session/{id}   — clear session
  GET  /api/health           — liveness probe
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.orchestrator import Orchestrator
from config import get_settings
from memory.manager import MemoryManager
from models.schemas import (
    AgentResponse,
    AnalysisRequest,
    SessionMemory,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
settings = get_settings()

app = FastAPI(
    title="Stock Analyst Agent API",
    description="Multi-agent AI system for stock market analysis and recommendations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons (created once at startup) ─────────────────────────────────────
memory_manager = MemoryManager(
    redis_url=settings.redis_url,
    ttl_seconds=3600,
)
orchestrator = Orchestrator(memory=memory_manager)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "model": settings.agent_model}


@app.post("/api/analyze", response_model=AgentResponse)
async def analyze(request: AnalysisRequest) -> AgentResponse:
    """
    Main endpoint. Accepts a user message + session context, runs the
    orchestrator pipeline, and returns a structured recommendation response.
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured on the server.",
        )

    log.info(
        "analyze | session=%s mode=%s msg=%r",
        request.session_id,
        request.mode,
        request.message[:80],
    )

    try:
        response = await orchestrator.handle(request)
        log.info(
            "analyze | session=%s iterations=%d tools=%d recs=%d",
            request.session_id,
            response.iterations,
            response.tool_calls_made,
            len(response.recommendations),
        )
        return response
    except Exception as exc:
        log.exception("analyze | unhandled error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/session/{session_id}", response_model=SessionMemory)
async def get_session(session_id: str) -> SessionMemory:
    """Return the current session memory (holdings, history, cached tickers)."""
    return memory_manager.load(session_id)


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Clear all session data."""
    memory_manager.delete(session_id)
    return {"deleted": session_id}


@app.post("/api/session/new")
async def new_session() -> dict:
    """Generate a fresh session ID."""
    return {"session_id": str(uuid.uuid4())}
