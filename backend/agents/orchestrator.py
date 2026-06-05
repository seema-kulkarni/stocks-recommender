"""
Orchestrator Agent — the top-level coordinator.

Responsibilities:
1. Parse user intent (individual vs general) using the LLM + classify_intent tool.
2. Extract any stock holdings the user mentions via extract_holdings tool.
3. Persist holdings and conversation turns to the MemoryManager.
4. Invoke the appropriate sub-agent with enriched context.
5. Return a fully-assembled AgentResponse.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import anthropic

from agents.base import _make_client
from agents.individual import IndividualStockAgent
from agents.general import GeneralMarketAgent
from agents.prompts import ORCHESTRATOR_SYSTEM
from config import get_settings
from memory.manager import MemoryManager
from models.schemas import (
    AgentMode, AgentResponse, AnalysisRequest,
    HoldingContext, ChatMessage,
)
from tools.registry import ALL_TOOLS

log = logging.getLogger(__name__)
settings = get_settings()


class Orchestrator:
    """
    Entry point for every user message.
    Instantiated once at app startup and reused across requests.
    """

    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self.client = _make_client()
        self._individual = IndividualStockAgent()
        self._general = GeneralMarketAgent()

    # ── Public API ────────────────────────────────────────────────────────────

    async def handle(self, request: AnalysisRequest) -> AgentResponse:
        session_id = request.session_id
        mem = self.memory.load(session_id)

        # 1. Persist incoming known holdings (sent by frontend)
        for h in request.known_holdings:
            self.memory.upsert_holding(session_id, h)

        # 2. Parse intent + extract any new holdings from the message
        intent_result = await self._parse_intent(request.message, mem)
        mode: AgentMode = intent_result["mode"]
        tickers: list[str] = intent_result.get("tickers", [])
        new_holdings: list[HoldingContext] = intent_result.get("holdings", [])

        # Persist new holdings extracted from this message
        for h in new_holdings:
            self.memory.upsert_holding(session_id, h)

        # Update last-mentioned tickers
        if tickers:
            self.memory.set_tickers(session_id, tickers)

        # Reload memory (with updates)
        mem = self.memory.load(session_id)

        # 3. Build context dict for the sub-agent
        context = self._build_context(mem, mode, tickers)

        # 4. Build conversation history for the sub-agent
        history = [{"role": t.role, "content": t.content} for t in mem.conversation[-8:]]

        # 5. Invoke the right sub-agent
        if mode == AgentMode.INDIVIDUAL and tickers:
            ticker = tickers[0].upper()
            context["ticker"] = ticker
            # Attach holding context if user holds this stock
            holding = next((h for h in mem.holdings if h.ticker == ticker), None)
            if holding:
                context["holding"] = holding.model_dump()
            result = await self._individual.run(request.message, history, context)
        else:
            result = await self._general.run(request.message, history, context)

        # 6. Persist conversation turns
        self.memory.append_turn(session_id, "user", request.message)
        self.memory.append_turn(session_id, "assistant", result["raw_text"][:2000])

        return AgentResponse(
            session_id=session_id,
            mode=mode,
            narrative=result["narrative"],
            recommendations=result["recommendations"],
            tool_calls_made=result["tool_calls_made"],
            iterations=result["iterations"],
            raw_assistant_text=result["raw_text"],
        )

    # ── Intent parsing ────────────────────────────────────────────────────────

    async def _parse_intent(
        self,
        message: str,
        mem,
    ) -> dict[str, Any]:
        """
        Use a lightweight LLM call (with classify_intent + extract_holdings tools)
        to determine mode, tickers, and any holdings mentioned.
        """
        response = self.client.messages.create(
            model=settings.agent_model,
            max_tokens=512,
            system=ORCHESTRATOR_SYSTEM,
            tools=ALL_TOOLS,
            messages=[{"role": "user", "content": message}],
        )

        result: dict[str, Any] = {"mode": AgentMode.GENERAL, "tickers": [], "holdings": []}

        for block in response.content:
            if block.type != "tool_use":
                continue

            inp = block.input or {}

            if block.name == "classify_intent":
                raw_mode = inp.get("mode", "general")
                result["mode"] = AgentMode.INDIVIDUAL if raw_mode == "individual" else AgentMode.GENERAL
                result["tickers"] = [t.upper() for t in inp.get("tickers", [])]

            elif block.name == "extract_holdings":
                ticker = inp.get("ticker", "").upper()
                if ticker:
                    result["holdings"].append(
                        HoldingContext(
                            ticker=ticker,
                            buy_price=inp.get("buy_price"),
                            quantity=inp.get("quantity"),
                            buy_date=inp.get("buy_date"),
                        )
                    )
                    # If a holding is mentioned, treat it as individual mode
                    if result["mode"] == AgentMode.GENERAL and ticker:
                        result["mode"] = AgentMode.INDIVIDUAL
                        if ticker not in result["tickers"]:
                            result["tickers"].append(ticker)

        # Fallback: regex scan for known tickers if LLM missed them
        if not result["tickers"]:
            from tools.registry import FULL_WATCHLIST
            all_tickers = {w["ticker"] for w in FULL_WATCHLIST}
            found = re.findall(r'\b([A-Z]{2,5})\b', message.upper())
            matched = [t for t in found if t in all_tickers]
            if matched:
                result["tickers"] = matched
                if len(matched) == 1:
                    result["mode"] = AgentMode.INDIVIDUAL

        return result

    # ── Context builder ───────────────────────────────────────────────────────

    def _build_context(self, mem, mode: AgentMode, tickers: list[str]) -> dict[str, Any]:
        return {
            "mode": mode.value,
            "holdings": [h.model_dump() for h in mem.holdings],
            "last_tickers": mem.last_tickers_mentioned,
            "session_id": mem.session_id,
        }
