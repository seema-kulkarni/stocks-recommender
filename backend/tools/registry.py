"""
Tool registry for the Stock Analyst Agent framework.

All agents share this registry. It defines the Anthropic tool schemas
and provides a simple TTL cache so repeated queries within a session
don't re-hit the same source.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Optional

log = logging.getLogger(__name__)

# ── In-process tool result cache ─────────────────────────────────────────────
# key → (result_str, expiry_epoch)
_cache: dict[str, tuple[str, float]] = {}


def _cache_key(tool_name: str, query: str) -> str:
    return hashlib.md5(f"{tool_name}:{query}".encode()).hexdigest()


def cache_get(tool_name: str, query: str, ttl: int) -> Optional[str]:
    key = _cache_key(tool_name, query)
    if key in _cache:
        result, expiry = _cache[key]
        if time.time() < expiry:
            return result
        del _cache[key]
    return None


def cache_set(tool_name: str, query: str, result: str, ttl: int) -> None:
    key = _cache_key(tool_name, query)
    _cache[key] = (result, time.time() + ttl)


# ── Anthropic tool schemas ────────────────────────────────────────────────────

WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20250305",
    "name": "web_search",
}

# Additional custom tools the LLM can "call" symbolically.
# The orchestrator intercepts these and runs the actual logic.
CUSTOM_TOOLS: list[dict[str, Any]] = [
    {
        "name": "extract_holdings",
        "description": (
            "Call this when the user mentions they own, bought, or hold a stock. "
            "Extract the ticker, approximate buy price (if stated), and quantity (if stated)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker":    {"type": "string", "description": "Uppercase ticker symbol, e.g. DELL"},
                "buy_price": {"type": "number", "description": "Price per share paid, if mentioned"},
                "quantity":  {"type": "number", "description": "Number of shares, if mentioned"},
                "buy_date":  {"type": "string", "description": "ISO date purchased, if mentioned"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "classify_intent",
        "description": (
            "Classify the user's query. "
            "Returns mode='individual' if asking about a single stock, "
            "'general' if asking for broad market recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode":    {"type": "string", "enum": ["individual", "general"]},
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tickers explicitly mentioned, if any",
                },
            },
            "required": ["mode"],
        },
    },
]

ALL_TOOLS: list[dict[str, Any]] = [WEB_SEARCH_TOOL] + CUSTOM_TOOLS


# ── Watchlists ────────────────────────────────────────────────────────────────

SP500_AI_WATCHLIST: list[dict[str, str]] = [
    {"ticker": "DELL",  "name": "Dell Technologies"},
    {"ticker": "ARM",   "name": "Arm Holdings"},
    {"ticker": "AMD",   "name": "Advanced Micro Devices"},
    {"ticker": "INTC",  "name": "Intel Corp"},
    {"ticker": "NOW",   "name": "ServiceNow"},
    {"ticker": "AMZN",  "name": "Amazon"},
    {"ticker": "MSFT",  "name": "Microsoft"},
    {"ticker": "GOOGL", "name": "Alphabet"},
    {"ticker": "IBM",   "name": "IBM Corp"},
    {"ticker": "NVDA",  "name": "NVIDIA"},
    {"ticker": "PLTR",  "name": "Palantir Technologies"},
    {"ticker": "META",  "name": "Meta Platforms"},
    {"ticker": "AVGO",  "name": "Broadcom"},
    {"ticker": "MU",    "name": "Micron Technology"},
    {"ticker": "MRVL",  "name": "Marvell Technology"},
]

QUANTUM_WATCHLIST: list[dict[str, str]] = [
    {"ticker": "IONQ",  "name": "IonQ"},
    {"ticker": "RGTI",  "name": "Rigetti Computing"},
    {"ticker": "QUBT",  "name": "Quantum Computing Inc."},
    {"ticker": "QMCO",  "name": "Quantum-Si"},
    {"ticker": "IBMQ",  "name": "IBM Quantum (via IBM)"},
]

AI_WATCHLIST: list[dict[str, str]] = [
    {"ticker": "NBIS",  "name": "Nebius Group"},
    {"ticker": "AI",    "name": "C3.ai"},
    {"ticker": "SOUN",  "name": "SoundHound AI"},
    {"ticker": "BBAI",  "name": "BigBear.ai"},
    {"ticker": "PATH",  "name": "UiPath"},
    {"ticker": "CRWV",  "name": "CoreWeave"},
    {"ticker": "ALAB",  "name": "Astera Labs"},
]

FULL_WATCHLIST = SP500_AI_WATCHLIST + QUANTUM_WATCHLIST + AI_WATCHLIST
