import logging
import re

import anthropic

from models.schemas import (
    AgentResponse,
    AgentMode,
    AnalysisRequest,
    HoldingContext,
)
from agents.individual import IndividualStockAgent
from agents.general import GeneralMarketAgent
from agents.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from memory.manager import MemoryManager
from tools.registry import ALL_TOOLS

logger = logging.getLogger(__name__)

# Common words to exclude when scanning for ticker symbols
TICKER_EXCLUSIONS = {
    "I", "A", "AI", "AND", "OR", "THE", "IS", "IN", "AT", "BUY",
    "SELL", "HOLD", "MY", "ME", "IT", "DO", "NOT", "SO", "BE",
    "TO", "OF", "ON", "AN", "AS", "BY", "US", "AM", "PM",
}


class Orchestrator:
    """
    Top-level router.
    1. Parses intent from the user message (individual vs general mode)
    2. Merges known holdings from request into session memory
    3. Delegates to IndividualStockAgent or GeneralMarketAgent
    4. Returns a structured AgentResponse
    """

    def __init__(self, memory_manager: MemoryManager, api_key: str):
        self.memory = memory_manager
        self.api_key = api_key

    async def handle(self, request: AnalysisRequest) -> AgentResponse:
        session_id = request.session_id

        # ── 1. Restore / initialise session ──────────────────────────────────
        session = await self.memory.get_or_create_session(session_id)

        # ── 2. Merge holdings from request into session memory ────────────────
        if request.known_holdings:
            await self.memory.upsert_holdings(session_id, request.known_holdings)
            session = await self.memory.get_or_create_session(session_id)

        all_holdings: list[HoldingContext] = session.get("holdings", [])

        # ── 3. Determine mode ─────────────────────────────────────────────────
        mode, detected_tickers = self._classify(request)
        effective_mode = request.mode if request.mode else mode

        logger.info(
            f"[Orchestrator] session={session_id} "
            f"mode={effective_mode} tickers={detected_tickers}"
        )

        # ── 4. Build conversation history for the sub-agent ───────────────────
        history = request.conversation_history or []
        messages = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": request.message})

        # ── 5. Route to sub-agent ─────────────────────────────────────────────
        if effective_mode == AgentMode.individual:
            ticker = detected_tickers[0] if detected_tickers else None
            holding = self._find_holding(ticker, all_holdings) if ticker else None

            agent = IndividualStockAgent(
                api_key=self.api_key,
                ticker=ticker,
                holding=holding,
            )
            system = agent.system_prompt(
                ticker=ticker,
                holding=holding,
                holdings=all_holdings,
            )
        else:
            agent = GeneralMarketAgent(api_key=self.api_key)
            system = agent.system_prompt(holdings=all_holdings)

        narrative, recommendations = await agent.run(
            messages=messages,
            system=system,
            session_id=session_id,
        )

        # ── 6. Persist conversation turn ──────────────────────────────────────
        await self.memory.append_conversation(
            session_id,
            role="user",
            content=request.message,
        )
        await self.memory.append_conversation(
            session_id,
            role="assistant",
            content=narrative,
        )

        # ── 7. Build and return response ──────────────────────────────────────
        return agent.build_response(
            session_id=session_id,
            mode=effective_mode,
            narrative=narrative,
            recommendations=recommendations,
            raw_text=narrative,
        )

    def _classify(self, request: AnalysisRequest) -> tuple[AgentMode, list[str]]:
        """
        Determine agent mode and extract ticker symbols from the user message.
        Uses a lightweight heuristic — no extra API call needed.
        """
        text = request.message
        upper_text = text.upper()

        # Extract candidate tickers (2-5 uppercase letters)
        raw_tickers = re.findall(r'\b([A-Z]{2,5})\b', upper_text)
        tickers = [t for t in raw_tickers if t not in TICKER_EXCLUSIONS]

        # Individual-mode signals
        individual_signals = [
            "should i buy", "should i sell", "should i hold",
            "i bought", "i own", "i hold", "i have",
            "my position", "my stock", "my shares",
            "analyze ", "deep dive", "what about", "tell me about",
            "buy more", "add more", "take profit", "cut loss",
        ]
        text_lower = text.lower()
        has_individual_signal = any(s in text_lower for s in individual_signals)

        # If exactly one ticker detected OR individual signal present → individual mode
        if tickers and (len(tickers) == 1 or has_individual_signal):
            return AgentMode.individual, tickers[:1]

        return AgentMode.general, tickers

    def _find_holding(
        self,
        ticker: str | None,
        holdings: list[HoldingContext],
    ) -> HoldingContext | None:
        """Return the holding record for a given ticker, if the user holds it."""
        if not ticker:
            return None
        for h in holdings:
            h_ticker = h.ticker if isinstance(h, HoldingContext) else h.get("ticker")
            if h_ticker and h_ticker.upper() == ticker.upper():
                return h
        return None
