"""
Individual Stock Agent — deep-dives a single ticker.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from agents.base import BaseAgent
from agents.prompts import individual_prompt
from config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


class IndividualStockAgent(BaseAgent):
    """
    Specialist sub-agent for single-ticker analysis.

    Given a ticker (and optional user context like buy price),
    this agent runs a focused ReAct loop searching for:
    - Current price and intraday movement
    - Recent earnings / EPS vs estimates
    - Analyst ratings and price targets
    - News and catalysts
    - Bull / bear scenarios
    """

    name = "individual_stock"

    @property
    def system_prompt(self) -> str:
        return individual_prompt(
            max_iterations=settings.max_react_iterations,
            min_confidence=settings.min_confidence,
            year=datetime.date.today().year,
        )

    def _build_messages(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Inject ticker-specific framing into the user message."""
        ticker = context.get("ticker", "")
        holding = context.get("holding")

        prefix_lines: list[str] = []
        if ticker:
            prefix_lines.append(f"[TARGET TICKER: {ticker}]")
        if holding:
            bp = holding.get("buy_price")
            qty = holding.get("quantity")
            bd  = holding.get("buy_date")
            parts = [f"[USER HOLDS {ticker}"]
            if bp:  parts.append(f"bought at ${bp:.2f}")
            if qty: parts.append(f"x{qty} shares")
            if bd:  parts.append(f"on {bd}")
            prefix_lines.append(" ".join(parts) + "]")

        prefix = "\n".join(prefix_lines) + "\n\n" if prefix_lines else ""

        messages = super()._build_messages(
            prefix + user_message, history, context
        )
        return messages
