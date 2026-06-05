"""
General Market Agent — analyses a basket of AI, quantum, and S&P 500 tech stocks.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from agents.base import BaseAgent
from agents.prompts import general_prompt
from config import get_settings
from tools.registry import SP500_AI_WATCHLIST, QUANTUM_WATCHLIST, AI_WATCHLIST

log = logging.getLogger(__name__)
settings = get_settings()


def _tickers(watchlist: list[dict[str, str]]) -> str:
    return ", ".join(w["ticker"] for w in watchlist)


class GeneralMarketAgent(BaseAgent):
    """
    Specialist sub-agent for broad market basket analysis.

    Covers the full watchlist (S&P 500 AI tech + quantum + pure-play AI),
    prioritising names with the strongest near-term signals.
    """

    name = "general_market"

    @property
    def system_prompt(self) -> str:
        now = datetime.date.today()
        return general_prompt(
            sp500_tickers=_tickers(SP500_AI_WATCHLIST),
            quantum_tickers=_tickers(QUANTUM_WATCHLIST),
            ai_tickers=_tickers(AI_WATCHLIST),
            max_iterations=settings.max_react_iterations,
            min_confidence=settings.min_confidence,
            month=now.strftime("%B"),
            year=now.year,
        )
