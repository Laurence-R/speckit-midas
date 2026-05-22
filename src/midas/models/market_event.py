"""MarketEvent dataclass, EventType and Sentiment enums."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    FINANCIAL_REPORT = "financial_report"
    INVESTOR_CONFERENCE = "investor_conference"
    MATERIAL_NEWS = "material_news"
    GENERAL_ANNOUNCEMENT = "general_announcement"

    @property
    def priority(self) -> int:
        return {
            EventType.FINANCIAL_REPORT: 1,
            EventType.INVESTOR_CONFERENCE: 2,
            EventType.MATERIAL_NEWS: 3,
            EventType.GENERAL_ANNOUNCEMENT: 4,
        }[self]

    @property
    def display_label(self) -> str:
        return {
            EventType.FINANCIAL_REPORT: "財報",
            EventType.INVESTOR_CONFERENCE: "法說會",
            EventType.MATERIAL_NEWS: "重大訊息",
            EventType.GENERAL_ANNOUNCEMENT: "一般公告",
        }[self]


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class MarketEvent:
    symbol: str
    event_date: str  # YYYY-MM-DD
    event_type: EventType
    occurred_at: datetime
    title: str
    source_url: str  # MUST NOT be empty
    source_name: str
    fetched_at: datetime
    description: str = ""  # raw news body/description (not persisted)
    ai_summary: str | None = None
    ai_summary_generated_at: datetime | None = None
    ai_model: str | None = None
    sentiment: Sentiment | None = None
    disclaimer: str = "此為 AI 摘要，僅供參考，不構成投資建議。"
    id: int | None = None

    @property
    def event_type_priority(self) -> int:
        return self.event_type.priority
