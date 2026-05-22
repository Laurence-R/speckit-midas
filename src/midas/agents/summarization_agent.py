"""Summarization agent: batch LLM event summarization with quota control."""
from __future__ import annotations

import json
import logging
from typing import Any

from midas.agents.interfaces import ISummarizationAgent
from midas.exceptions import LLMQuotaExceededError
from midas.integrations.gemini_client import SYSTEM_PROMPT, GeminiClient
from midas.models.market_event import MarketEvent, Sentiment

logger = logging.getLogger(__name__)

_VALID_SENTIMENTS = {s.value for s in Sentiment}


class SummarizationAgent(ISummarizationAgent):
    """Calls Gemini LLM once per symbol to summarise a batch of events."""

    def __init__(self, gemini_client: GeminiClient | None = None) -> None:
        self._client = gemini_client or GeminiClient()

    # ------------------------------------------------------------------
    # ISummarizationAgent
    # ------------------------------------------------------------------

    def summarize_events(
        self, symbol: str, events: list[MarketEvent]
    ) -> list[MarketEvent]:
        """Summarise all *events* for *symbol* in a single LLM call.

        On failure (quota, network, parse error) the events are returned
        unchanged (``ai_summary = None``).
        """
        if not events:
            return events

        try:
            user_text = self._build_prompt(events)
            raw_response = self._client.generate(
                system_prompt=SYSTEM_PROMPT,
                user_text=user_text,
            )
            parsed = self._parse_response(raw_response)
            return self._apply_summaries(events, parsed)
        except LLMQuotaExceededError:
            logger.info("SummarizationAgent: daily LLM quota exceeded — skipping %s", symbol)
            return events
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SummarizationAgent: LLM call failed for %s: %s", symbol, exc
            )
            return events

    def get_daily_usage(self) -> tuple[int, int]:
        return self._client.get_daily_usage()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(events: list[MarketEvent]) -> str:
        lines = [
            "請為以下公告逐一生成新聞摘要與長期投資視角的分析解讀，輸出純 JSON：",
            '{"events": [{"id": <int>, "summary": <str 依【新聞摘要】+【分析解讀】格式>, "sentiment": "positive|neutral|negative"}]}',
            "",
        ]
        for i, e in enumerate(events):
            lines.append(f"[{i}] 標題：{e.title}")
            if e.description:
                lines.append(f"    報導內容：{e.description}")
        return "\n".join(lines)

    @staticmethod
    def _parse_response(raw: str) -> list[dict[str, Any]]:
        """Parse LLM JSON response. Returns empty list on any parse error."""
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        try:
            data = json.loads(text)
            return data.get("events", [])
        except json.JSONDecodeError as exc:
            logger.warning("SummarizationAgent: JSON parse error: %s", exc)
            return []

    @staticmethod
    def _apply_summaries(
        events: list[MarketEvent], parsed: list[dict[str, Any]]
    ) -> list[MarketEvent]:
        """Apply parsed summaries to the event list by index."""
        from datetime import datetime
        for item in parsed:
            idx = item.get("id")
            if idx is None or not isinstance(idx, int) or idx >= len(events):
                continue
            summary = item.get("summary", "")
            sentiment_raw = item.get("sentiment", "")

            # Validate: summary must be non-trivially short or excessively long
            if not (80 <= len(summary) <= 800):
                logger.debug(
                    "SummarizationAgent: summary length %d out of range for event %d",
                    len(summary), idx,
                )
                continue

            # Validate: sentiment must be one of the three allowed values
            if sentiment_raw not in _VALID_SENTIMENTS:
                sentiment_raw = None  # type: ignore[assignment]

            events[idx].ai_summary = summary
            events[idx].sentiment = Sentiment(sentiment_raw) if sentiment_raw else None
            events[idx].ai_summary_generated_at = datetime.now()

        return events
