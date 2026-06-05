from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from models.schemas import AnalysisRequest, AgentResponse
from agents.orchestrator import Orchestrator
from memory.manager import MemoryManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Stock Analyst API starting up...")
    yield
    logger.info("Stock Analyst API shutting down...")


app = FastAPI(
    title="Stock Analyst Agent",
    description="Multi-agent AI stock analysis powered by Claude",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_manager = MemoryManager()


def _validate_api_key(x_api_key: str | None) -> str:
    """
    Validate the Anthropic API key passed from the frontend.
    Falls back to the environment variable if no header is provided
    (useful for local dev / Docker where the key is in .env).
    """
    if x_api_key and x_api_key.startswith("sk-ant-"):
        return x_api_key

    env_key = os.getenv("ANTHROPIC_API_KEY", "")
    if env_key.startswith("sk-ant-"):
        return env_key

    raise HTTPException(
        status_code=401,
        detail="Valid Anthropic API key required. "
               "Pass it as the X-API-Key header (starting with sk-ant-).",
    )


@app.post("/api/analyze", response_model=AgentResponse)
async def analyze(
    request: AnalysisRequest,
    x_api_key: str | None = Header(default=None),
):
    """
    Main analysis endpoint.
    Accepts an optional X-API-Key header containing the user's Anthropic key.
    Falls back to the ANTHROPIC_API_KEY environment variable if not provided.
    """
    api_key = _validate_api_key(x_api_key)

    try:
        orchestrator = Orchestrator(
            memory_manager=memory_manager,
            api_key=api_key,
        )
        response = await orchestrator.handle(request)
        return response
    except Exception as e:
        logger.exception("Error during analysis")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session(
    session_id: str,
    x_api_key: str | None = Header(default=None),
):
    _validate_api_key(x_api_key)
    session = await memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/api/session/{session_id}")
async def delete_session(
    session_id: str,
    x_api_key: str | None = Header(default=None),
):
    _validate_api_key(x_api_key)
    await memory_manager.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.post("/api/session/new")
async def new_session(x_api_key: str | None = Header(default=None)):
    _validate_api_key(x_api_key)
    import uuid
    session_id = str(uuid.uuid4())
    await memory_manager.init_session(session_id)
    return {"session_id": session_id}


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "stock-analyst-agent"}
