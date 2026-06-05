import json
import re
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import anthropic

from models.schemas import AgentResponse, StockRecommendation, Recommendation
from tools.registry import ALL_TOOLS, TOOL_CACHE

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Shared ReAct loop engine used by all sub-agents.
    Think → Act (tool call) → Observe (tool result) → Judge (confident enough?)
    Loops up to MAX_REACT_ITERATIONS times, then outputs final response.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_iterations: int = 3,
        min_confidence: int = 65,
        tool_cache_ttl: int = 900,
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_iterations = max_iterations
        self.min_confidence = min_confidence
        self.tool_cache_ttl = tool_cache_ttl
        self.tool_calls_made = 0
        self.iterations = 0

    @abstractmethod
    def system_prompt(self, **kwargs) -> str:
        """Return the system prompt for this agent."""
        ...

    async def run(
        self,
        messages: list[dict],
        system: str,
        session_id: str,
    ) -> tuple[str, list[StockRecommendation]]:
        """
        Execute the ReAct loop.
        Returns (narrative, recommendations).
        """
        self.tool_calls_made = 0
        self.iterations = 0
        conversation = list(messages)

        for iteration in range(self.max_iterations):
            self.iterations = iteration + 1
            logger.info(f"[{self.__class__.__name__}] Iteration {self.iterations}")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                tools=ALL_TOOLS,
                messages=conversation,
            )

            # Append assistant turn to conversation
            conversation.append({"role": "assistant", "content": response.content})

            # If no tool calls, we're done
            if response.stop_reason == "end_turn":
                raw_text = self._extract_text(response.content)
                recommendations = self._parse_stock_table(raw_text)
                narrative = self._extract_narrative(raw_text)
                return narrative, recommendations

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    self.tool_calls_made += 1
                    result = self._dispatch_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            if tool_results:
                conversation.append({"role": "user", "content": tool_results})

        # Max iterations reached — extract whatever we have
        raw_text = self._extract_text(response.content)
        recommendations = self._parse_stock_table(raw_text)
        narrative = self._extract_narrative(raw_text)
        return narrative, recommendations

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        """Route a tool call to its handler. Returns the result as a string."""
        logger.info(f"Tool call: {tool_name} | input: {tool_input}")

        if tool_name == "web_search":
            return self._handle_web_search(tool_input)

        if tool_name == "classify_intent":
            return self._handle_classify_intent(tool_input)

        if tool_name == "extract_holdings":
            return self._handle_extract_holdings(tool_input)

        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def _handle_web_search(self, tool_input: dict) -> str:
        """
        The Anthropic SDK handles web_search natively — this method is here
        as a fallback handler for logging. The actual result comes back from
        the API automatically via the built-in web_search tool.
        """
        query = tool_input.get("query", "")
        cache_key = f"search:{query}"

        cached = TOOL_CACHE.get(cache_key)
        if cached and (time.time() - cached["ts"]) < self.tool_cache_ttl:
            logger.info(f"Cache hit for query: {query}")
            return cached["result"]

        # The SDK handles the actual search — we just log and return a placeholder
        # The real result is injected by the Anthropic API response pipeline
        result = json.dumps({"query": query, "status": "dispatched_to_anthropic"})
        TOOL_CACHE[cache_key] = {"result": result, "ts": time.time()}
        return result

    def _handle_classify_intent(self, tool_input: dict) -> str:
        """Classify user intent as individual or general mode."""
        text = tool_input.get("text", "").lower()
        tickers = re.findall(r'\b[A-Z]{2,5}\b', tool_input.get("text", ""))

        # Common words to exclude from ticker detection
        exclusions = {"I", "A", "AI", "AND", "OR", "THE", "IS", "IN", "AT",
                      "BUY", "SELL", "HOLD", "MY", "ME", "IT", "DO", "NOT"}
        tickers = [t for t in tickers if t not in exclusions]

        individual_signals = [
            "should i buy", "should i sell", "should i hold",
            "i bought", "i own", "i hold", "my position",
            "analyze", "deep dive", "what about", "tell me about"
        ]
        is_individual = any(s in text for s in individual_signals) or len(tickers) == 1

        return json.dumps({
            "mode": "individual" if is_individual else "general",
            "detected_tickers": tickers,
        })

    def _handle_extract_holdings(self, tool_input: dict) -> str:
        """Extract ticker and buy price from user message."""
        text = tool_input.get("text", "")
        tickers = re.findall(r'\b([A-Z]{2,5})\b', text)
        prices = re.findall(r'\$?([\d,]+\.?\d*)', text)

        holdings = []
        for i, ticker in enumerate(tickers):
            if ticker in {"I", "A", "AND", "OR", "THE", "BUY", "SELL"}:
                continue
            price = float(prices[i].replace(",", "")) if i < len(prices) else None
            holdings.append({"ticker": ticker, "buy_price": price})

        return json.dumps({"holdings": holdings})

    def _extract_text(self, content: list) -> str:
        """Concatenate all text blocks from an API response."""
        return "\n".join(
            block.text for block in content
            if hasattr(block, "text")
        ).strip()

    def _extract_narrative(self, raw_text: str) -> str:
        """Strip the <stock-table> block from text to get the narrative."""
        narrative = re.sub(
            r"<stock-table>.*?</stock-table>",
            "",
            raw_text,
            flags=re.DOTALL,
        ).strip()
        return narrative or raw_text

    def _parse_stock_table(self, raw_text: str) -> list[StockRecommendation]:
        """
        Parse the <stock-table>...</stock-table> JSON block from LLM output.
        Returns a list of StockRecommendation objects.
        """
        match = re.search(
            r"<stock-table>(.*?)</stock-table>",
            raw_text,
            re.DOTALL,
        )
        if not match:
            logger.warning("No <stock-table> block found in response")
            return []

        raw_json = match.group(1).strip()

        # Strip markdown code fences if present
        raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
        raw_json = re.sub(r"\s*```$", "", raw_json)

        try:
            items: list[dict[str, Any]] = json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse stock-table JSON: {e}\nRaw: {raw_json}")
            return []

        recommendations = []
        for item in items:
            try:
                rec_str = item.get("rec", "HOLD").upper()
                # Normalise variations
                rec_map = {
                    "STRONG BUY": Recommendation.STRONG_BUY,
                    "GOOD BUY": Recommendation.GOOD_BUY,
                    "HOLD": Recommendation.HOLD,
                    "GOOD SELL": Recommendation.GOOD_SELL,
                    "STRONG SELL": Recommendation.STRONG_SELL,
                    "BUY": Recommendation.GOOD_BUY,
                    "SELL": Recommendation.GOOD_SELL,
                }
                recommendation = rec_map.get(rec_str, Recommendation.HOLD)

                confidence = int(item.get("confidence", 70))
                # Skip low-confidence recommendations
                if confidence < self.min_confidence:
                    logger.info(
                        f"Skipping {item.get('ticker')} — "
                        f"confidence {confidence} < {self.min_confidence}"
                    )
                    continue

                stock_rec = StockRecommendation(
                    ticker=item.get("ticker", "???"),
                    name=item.get("name", item.get("ticker", "Unknown")),
                    current_price=item.get("price", item.get("current_price", "N/A")),
                    recommendation=recommendation,
                    reason=item.get("reason", ""),
                    target_price=item.get("target", item.get("target_price", "N/A")),
                    valid_until=item.get("valid_until", "Next earnings"),
                    confidence=confidence,
                    catalysts=item.get("catalysts", []),
                    risks=item.get("risks", []),
                    user_pnl_pct=item.get("user_pnl_pct"),
                )
                recommendations.append(stock_rec)
            except Exception as e:
                logger.error(f"Error parsing recommendation item: {e} | item: {item}")
                continue

        return recommendations

    def build_response(
        self,
        session_id: str,
        mode: str,
        narrative: str,
        recommendations: list[StockRecommendation],
        raw_text: str,
    ) -> AgentResponse:
        return AgentResponse(
            session_id=session_id,
            mode=mode,
            narrative=narrative,
            recommendations=recommendations,
            tool_calls_made=self.tool_calls_made,
            iterations=self.iterations,
            raw_assistant_text=raw_text,
        )
