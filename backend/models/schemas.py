"""
Shared Pydantic models for the Stock Analyst Agent framework.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class AgentMode(str, Enum):
    INDIVIDUAL = "individual"
    GENERAL    = "general"


class Recommendation(str, Enum):
    STRONG_BUY  = "STRONG BUY"
    GOOD_BUY    = "GOOD BUY"
    HOLD        = "HOLD"
    GOOD_SELL   = "GOOD SELL"
    STRONG_SELL = "STRONG SELL"


# ── Inbound request ──────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class AnalysisRequest(BaseModel):
    """Body sent by the frontend for every user message."""
    message: str = Field(..., description="Natural-language user prompt")
    mode: AgentMode = Field(AgentMode.GENERAL, description="Agent mode override")
    session_id: str = Field(..., description="Browser-session UUID")
    conversation_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior turns for multi-turn context"
    )
    # Optional holdings the user has already mentioned in this session
    known_holdings: list[HoldingContext] = Field(default_factory=list)


# ── Holdings context ─────────────────────────────────────────────────────────

class HoldingContext(BaseModel):
    ticker: str
    buy_price: Optional[float] = None
    quantity: Optional[float] = None
    buy_date: Optional[str] = None   # ISO date string


# ── Per-stock recommendation ─────────────────────────────────────────────────

class StockRecommendation(BaseModel):
    ticker: str
    name: str
    current_price: str           # formatted, e.g. "$435.31"
    recommendation: Recommendation
    reason: str                  # 1-2 sentence rationale
    target_price: str            # e.g. "$500"
    valid_until: str             # e.g. "Q3 2026 earnings"
    confidence: int              # 0-100
    catalysts: list[str] = []    # short bullet catalysts
    risks: list[str] = []        # short bullet risks
    # Set when user holds the stock
    user_pnl_pct: Optional[float] = None


# ── Agent response ───────────────────────────────────────────────────────────

class AgentResponse(BaseModel):
    session_id: str
    mode: AgentMode
    narrative: str                          # market-context prose
    recommendations: list[StockRecommendation]
    tool_calls_made: int = 0               # telemetry
    iterations: int = 0                    # ReAct loop count
    raw_assistant_text: str = ""           # full LLM output (debug)


# ── Session memory ───────────────────────────────────────────────────────────

class SessionMemory(BaseModel):
    session_id: str
    holdings: list[HoldingContext] = Field(default_factory=list)
    conversation: list[ChatMessage] = Field(default_factory=list)
    last_tickers_mentioned: list[str] = Field(default_factory=list)
    # Cached recommendation results keyed by ticker
    ticker_cache: dict[str, Any] = Field(default_factory=dict)


# ── Tool result wrapper ──────────────────────────────────────────────────────

class ToolResult(BaseModel):
    tool_name: str
    query: str
    result: str
    cached: bool = False
