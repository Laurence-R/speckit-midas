"""Announcement agent: fetches FinMind TaiwanStockNews and classifies events."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from midas.agents.interfaces import IAnnouncementAgent
from midas.models.market_event import EventType, MarketEvent

if TYPE_CHECKING:
    from midas.integrations.finmind_client import FinMindClient

logger = logging.getLogger(__name__)
_TW_TZ = timezone(timedelta(hours=8))

# Keyword → EventType classification rules (evaluated in order)
_CLASSIFICATION_RULES: list[tuple[list[str], EventType]] = [
    (["財報", "年報", "季報", "盈餘", "每股", "EPS"], EventType.FINANCIAL_REPORT),
    (["法說", "法人說明會", "investor", "conference"], EventType.INVESTOR_CONFERENCE),
    (
        ["重大訊息", "重訊", "重大", "停業", "解散", "合併", "收購", "下市"],
        EventType.MATERIAL_NEWS,
    ),
]


class AnnouncementAgent(IAnnouncementAgent):
    """Fetches FinMind TaiwanStockNews, classifies events, returns MarketEvent objects."""

    def __init__(self, finmind_client: FinMindClient | None = None) -> None:
        self._client = finmind_client

    # ------------------------------------------------------------------
    # IAnnouncementAgent
    # ------------------------------------------------------------------

    def fetch_announcements(self, symbol: str, date: str) -> list[MarketEvent]:
        """Fetch, classify, and normalise news for *symbol* on/after *date*.

        Returns an empty list if the client is not configured, no news exists,
        or the API call fails.
        """
        if self._client is None:
            return []

        try:
            result = self._client.get_stock_news(symbol, date)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AnnouncementAgent: get_stock_news failed for %s: %s", symbol, exc)
            return []

        records = result.get("data", [])
        logger.info("AnnouncementAgent: %s on %s → %d news records", symbol, date, len(records))
        events: list[MarketEvent] = []
        for rec in records:
            try:
                event = self._normalize_news(rec, symbol, date)
                events.append(event)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "AnnouncementAgent: failed to normalise news record for %s: %s",
                    symbol,
                    exc,
                )
        return events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_event(self, title: str, page_code: str) -> EventType:
        """Return the EventType for the given *title* (and optional *page_code*)."""
        text = f"{title} {page_code}".lower()
        for keywords, event_type in _CLASSIFICATION_RULES:
            if any(kw.lower() in text for kw in keywords):
                return event_type
        return EventType.GENERAL_ANNOUNCEMENT

    def _normalize_news(self, rec: dict[str, Any], symbol: str, target_date: str) -> MarketEvent:
        """Convert a TaiwanStockNews record into a :class:`MarketEvent` dataclass."""
        title: str = rec.get("title", "").strip()
        description: str = rec.get("description", "").strip()
        date_raw: str = rec.get("date", "")
        source_url: str = rec.get("link", "")
        source_name: str = rec.get("source", "FinMind 新聞")

        # Use the update target date so events always appear on the day they were fetched.
        # The actual publication time is preserved in occurred_at.
        event_date = target_date  # YYYY-MM-DD

        occurred_at = self._parse_news_datetime(date_raw)

        event_type = self._classify_event(title, "")

        return MarketEvent(
            symbol=symbol,
            event_date=event_date,
            event_type=event_type,
            occurred_at=occurred_at,
            title=title,
            description=description,
            source_url=source_url or f"https://finmindtrade.com/analysis/#/data/api?stock_id={symbol}",
            source_name=source_name,
            fetched_at=datetime.now(),
        )

    @staticmethod
    def _parse_news_datetime(date_raw: str) -> datetime:
        """Parse FinMind news datetime and convert UTC -> UTC+8 (Taipei)."""
        if not date_raw:
            return datetime.now()

        normalized = date_raw.strip().replace("Z", "+00:00")
        dt: datetime
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            parsed = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    parsed = datetime.strptime(normalized, fmt)
                    break
                except ValueError:
                    continue
            if parsed is None:
                return datetime.now()
            dt = parsed

        # FinMind news timestamps are UTC; convert for Taiwan UI display.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_TW_TZ).replace(tzinfo=None)
