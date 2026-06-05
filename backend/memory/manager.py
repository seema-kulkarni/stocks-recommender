"""
Session memory manager.

Uses Redis when available; falls back to an in-process dict otherwise.
Each session stores conversation history, known holdings, recently
mentioned tickers, and a short-lived tool-result cache.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from models.schemas import SessionMemory, ChatMessage, HoldingContext

log = logging.getLogger(__name__)

# ── In-process fallback store ─────────────────────────────────────────────────
_local_store: dict[str, str] = {}


def _try_redis(redis_url: str):
    """Return a redis.Redis client or None if redis is unavailable."""
    try:
        import redis
        client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        log.info("Memory backend: Redis (%s)", redis_url)
        return client
    except Exception:
        log.info("Memory backend: in-process dict (Redis unavailable)")
        return None


class MemoryManager:
    """CRUD for SessionMemory objects."""

    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        self._redis = _try_redis(redis_url)
        self._ttl = ttl_seconds

    # ── raw helpers ───────────────────────────────────────────────────────────

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _load_raw(self, session_id: str) -> Optional[str]:
        key = self._key(session_id)
        if self._redis:
            return self._redis.get(key)
        return _local_store.get(key)

    def _save_raw(self, session_id: str, data: str) -> None:
        key = self._key(session_id)
        if self._redis:
            self._redis.setex(key, self._ttl, data)
        else:
            _local_store[key] = data

    # ── public API ────────────────────────────────────────────────────────────

    def load(self, session_id: str) -> SessionMemory:
        """Load or create a session."""
        raw = self._load_raw(session_id)
        if raw:
            try:
                return SessionMemory.model_validate_json(raw)
            except Exception:
                pass
        return SessionMemory(session_id=session_id)

    def save(self, memory: SessionMemory) -> None:
        self._save_raw(memory.session_id, memory.model_dump_json())

    def append_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        max_turns: int = 20,
    ) -> SessionMemory:
        """Append a conversation turn and persist."""
        mem = self.load(session_id)
        mem.conversation.append(ChatMessage(role=role, content=content))
        # Keep a rolling window to avoid unbounded growth
        if len(mem.conversation) > max_turns:
            mem.conversation = mem.conversation[-max_turns:]
        self.save(mem)
        return mem

    def upsert_holding(self, session_id: str, holding: HoldingContext) -> SessionMemory:
        """Add or update a holding in memory."""
        mem = self.load(session_id)
        mem.holdings = [h for h in mem.holdings if h.ticker != holding.ticker]
        mem.holdings.append(holding)
        self.save(mem)
        return mem

    def set_tickers(self, session_id: str, tickers: list[str]) -> None:
        mem = self.load(session_id)
        mem.last_tickers_mentioned = tickers
        self.save(mem)

    def cache_ticker_result(self, session_id: str, ticker: str, data: dict) -> None:
        mem = self.load(session_id)
        mem.ticker_cache[ticker] = data
        self.save(mem)

    def get_cached_ticker(self, session_id: str, ticker: str) -> Optional[dict]:
        mem = self.load(session_id)
        return mem.ticker_cache.get(ticker)

    def delete(self, session_id: str) -> None:
        key = self._key(session_id)
        if self._redis:
            self._redis.delete(key)
        else:
            _local_store.pop(key, None)
