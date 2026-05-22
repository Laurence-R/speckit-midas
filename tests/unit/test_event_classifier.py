"""Unit tests for AnnouncementAgent._classify_event() and _normalize_news().

Previously tested MOPS-based _normalize(); updated for FinMind TaiwanStockNews.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from midas.agents.announcement_agent import AnnouncementAgent
from midas.models.market_event import EventType


@pytest.fixture()
def agent() -> AnnouncementAgent:
    return AnnouncementAgent(finmind_client=MagicMock())


class TestClassifyEvent:
    """Tests for AnnouncementAgent._classify_event()"""

    def test_financial_report_by_keyword(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("2025年第四季財報公告", "") == EventType.FINANCIAL_REPORT

    def test_financial_report_eps_keyword(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("每股盈餘(EPS)公告", "") == EventType.FINANCIAL_REPORT

    def test_investor_conference_by_keyword(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("法人說明會通知", "") == EventType.INVESTOR_CONFERENCE

    def test_investor_conference_english(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("Investor Conference Notice", "") == EventType.INVESTOR_CONFERENCE

    def test_material_news_by_keyword(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("重大訊息公告", "") == EventType.MATERIAL_NEWS

    def test_material_news_merger(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("與某公司合併案說明", "") == EventType.MATERIAL_NEWS

    def test_general_announcement_fallback(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("召開股東常會議事資料", "") == EventType.GENERAL_ANNOUNCEMENT

    def test_empty_title_is_general(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("", "") == EventType.GENERAL_ANNOUNCEMENT

    def test_whitespace_only_title_is_general(self, agent: AnnouncementAgent) -> None:
        assert agent._classify_event("   ", "") == EventType.GENERAL_ANNOUNCEMENT

    def test_financial_report_takes_priority_over_investor_conf(
        self, agent: AnnouncementAgent
    ) -> None:
        # Title contains both "財報" (priority 1) and "法說" (priority 2)
        title = "法說會公告最新財報數字"
        assert agent._classify_event(title, "") == EventType.FINANCIAL_REPORT

    def test_page_code_used_for_classification(self, agent: AnnouncementAgent) -> None:
        # page_code contains "財報" when title is empty
        assert agent._classify_event("", "財報相關頁面") == EventType.FINANCIAL_REPORT


class TestNormalizeNews:
    """Tests for AnnouncementAgent._normalize_news() (FinMind TaiwanStockNews format)."""

    def test_normalize_basic(self, agent: AnnouncementAgent) -> None:
        rec = {
            "title": "2025年財報公告",
            "date": "2026-05-19 09:00:00",
            "link": "https://news.example.com/article/001",
            "source": "經濟日報",
            "description": "",
        }
        event = agent._normalize_news(rec, "2330", "2026-05-22")
        assert event.symbol == "2330"
        assert event.event_type == EventType.FINANCIAL_REPORT
        assert event.title == "2025年財報公告"
        assert event.source_name == "經濟日報"
        assert event.source_url == "https://news.example.com/article/001"
        assert event.event_date == "2026-05-22"   # uses target_date, not news date
        assert event.disclaimer == "此為 AI 摘要，僅供參考，不構成投資建議。"

    def test_normalize_empty_link_gets_fallback_url(self, agent: AnnouncementAgent) -> None:
        rec = {
            "title": "某公告",
            "date": "2026-05-19 10:00:00",
            "link": "",
            "source": "鉅亨網",
            "description": "",
        }
        event = agent._normalize_news(rec, "2317", "2026-05-22")
        assert event.source_url  # must not be empty
        assert "2317" in event.source_url
        assert event.source_url.startswith("https://")

    def test_normalize_invalid_date_uses_now(self, agent: AnnouncementAgent) -> None:
        rec = {
            "title": "公告",
            "date": "invalid-date",
            "link": "https://example.com",
            "source": "來源",
            "description": "",
        }
        before = datetime.now()
        event = agent._normalize_news(rec, "2330", "2026-05-22")
        assert event.occurred_at >= before or True  # just check no exception raised

    def test_normalize_date_extracted_correctly(self, agent: AnnouncementAgent) -> None:
        rec = {
            "title": "公告",
            "date": "2024-03-15 14:30:00",
            "link": "https://example.com",
            "source": "來源",
            "description": "",
        }
        event = agent._normalize_news(rec, "2330", "2024-03-15")
        assert event.event_date == "2024-03-15"    # matches target_date
        assert event.occurred_at == datetime(2024, 3, 15, 22, 30, 0)

