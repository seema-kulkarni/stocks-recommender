"""
BaseAgent — shared ReAct loop logic used by both sub-agents.

Handles:
- Building the Anthropic messages payload
- Running the think → act → observe → judge loop
- Extracting <stock-table> JSON from LLM output
- Telemetry (iteration count, tool calls made)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import anthropic

from config import get_settings
from models.schemas import StockRecommendation, Recommendation
from tools.registry import ALL_TOOLS, cache_get, cache_set

log = logging.getLogger(__name__)
settings = get_settings()


def _make_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


class BaseAgent:
    """
    Base class for all stock analyst sub-agents.
    Subclasses override `system_prompt` and optionally `build_user_message`.
    """

    name: str = "base"

    def __init__(self):
        self.client = _make_client()
        self.settings = settings

    @property
    def system_prompt(self) -> str:
        raise NotImplementedError

    # ── Core ReAct runner ─────────────────────────────────────────────────────

    async def run(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run the ReAct loop and return a structured result dict containing:
        - narrative: str
        - recommendations: list[StockRecommendation]
        - raw_text: str
        - iterations: int
        - tool_calls_made: int
        """
        messages = self._build_messages(user_message, conversation_history or [], context or {})

        full_text = ""
        tool_calls_made = 0
        iterations = 0

        for iteration in range(self.settings.max_react_iterations):
            iterations += 1
            log.debug("[%s] ReAct iteration %d", self.name, iteration + 1)

            response = self.client.messages.create(
                model=self.settings.agent_model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=ALL_TOOLS,
                messages=messages,
            )

            # Collect text and tool_use blocks
            assistant_content = []
            text_parts: list[str] = []

            for block in response.content:
                assistant_content.append(block)
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls_made += 1

            full_text += "\n".join(text_parts)

            # If no tool calls → the model is done
            if response.stop_reason == "end_turn":
                log.debug("[%s] Done after %d iterations", self.name, iterations)
                break

            # Process tool_use blocks → build tool_result messages
            tool_results = []
            for block in assistant_content:
                if block.type != "tool_use":
                    continue

                tool_input = block.input or {}
                result_str = await self._dispatch_tool(block.name, tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

            # Append assistant turn + tool results to message history
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        return {
            "raw_text": full_text,
            "narrative": self._extract_narrative(full_text),
            "recommendations": self._parse_stock_table(full_text),
            "iterations": iterations,
            "tool_calls_made": tool_calls_made,
        }

    # ── Tool dispatcher ───────────────────────────────────────────────────────

    async def _dispatch_tool(self, name: str, tool_input: dict) -> str:
        """Route a tool_use block to the right handler."""
        if name == "web_search":
            query = tool_input.get("query", "")
            return await self._web_search(query)
        elif name == "classify_intent":
            return json.dumps(tool_input)   # just echo back
        elif name == "extract_holdings":
            return json.dumps(tool_input)   # caller will persist
        else:
            return f"[Tool '{name}' not implemented]"

    async def _web_search(self, query: str) -> str:
        """
        Web search via a dedicated Anthropic API call with the web_search tool.
        Results are cached per query for TOOL_CACHE_TTL seconds.
        """
        cached = cache_get("web_search", query, self.settings.tool_cache_ttl)
        if cached:
            log.debug("[%s] Cache hit: %s", self.name, query[:60])
            return cached

        log.debug("[%s] Web search: %s", self.name, query[:60])

        # Delegate the actual web search to a lightweight Anthropic call
        search_response = self.client.messages.create(
            model=self.settings.agent_model,
            max_tokens=1024,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": query}],
        )

        parts: list[str] = []
        for block in search_response.content:
            if hasattr(block, "text"):
                parts.append(block.text)

        result = "\n".join(parts) if parts else "[No results]"
        cache_set("web_search", query, result, self.settings.tool_cache_ttl)
        return result

    # ── Message builder ───────────────────────────────────────────────────────

    def _build_messages(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build the messages list for the Anthropic API call."""
        messages: list[dict[str, Any]] = []

        # Prior conversation turns (keep last 10)
        for turn in history[-10:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

        # Inject session context into the user turn
        ctx_lines: list[str] = []
        if context.get("holdings"):
            holdings_str = ", ".join(
                f"{h['ticker']} (bought @ ${h.get('buy_price', '?')})"
                for h in context["holdings"]
            )
            ctx_lines.append(f"[USER HOLDINGS: {holdings_str}]")
        if context.get("last_tickers"):
            ctx_lines.append(f"[RECENTLY DISCUSSED: {', '.join(context['last_tickers'])}]")

        prefix = "\n".join(ctx_lines) + "\n\n" if ctx_lines else ""
        messages.append({"role": "user", "content": prefix + user_message})
        return messages

    # ── Response parsers ──────────────────────────────────────────────────────

    def _extract_narrative(self, text: str) -> str:
        """Extract the prose narrative (everything before the stock table)."""
        table_match = re.search(r"<stock-table>", text, re.IGNORECASE)
        if table_match:
            return text[: table_match.start()].strip()
        return text.strip()

    def _parse_stock_table(self, text: str) -> list[StockRecommendation]:
        """Parse <stock-table>[…JSON…]</stock-table> from LLM output."""
        pattern = re.compile(r"<stock-table>(.*?)</stock-table>", re.DOTALL | re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            return []

        raw_json = match.group(1).strip()
        # Strip markdown fences if present
        raw_json = re.sub(r"```(?:json)?", "", raw_json).strip().rstrip("`").strip()

        try:
            data = json.loads(raw_json)
            if not isinstance(data, list):
                data = [data]
        except json.JSONDecodeError as exc:
            log.warning("Failed to parse stock-table JSON: %s", exc)
            return []

        results: list[StockRecommendation] = []
        for item in data:
            try:
                rec_str = item.get("rec", "HOLD").upper()
                # Normalise aliases
                rec_str = rec_str.replace("BUY", "BUY").strip()
                try:
                    rec = Recommendation(rec_str)
                except ValueError:
                    rec = Recommendation.HOLD

                results.append(
                    StockRecommendation(
                        ticker=item.get("ticker", "?"),
                        name=item.get("name", ""),
                        current_price=str(item.get("price", "N/A")),
                        recommendation=rec,
                        reason=item.get("reason", ""),
                        target_price=str(item.get("target", "N/A")),
                        valid_until=item.get("valid_until", "Next earnings"),
                        confidence=int(item.get("confidence", 60)),
                        catalysts=item.get("catalysts", []),
                        risks=item.get("risks", []),
                    )
                )
            except Exception as exc:
                log.warning("Skipping malformed stock entry: %s — %s", item, exc)

        return results
