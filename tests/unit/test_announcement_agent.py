"""Unit tests for AnnouncementAgent with FinMind TaiwanStockNews."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from midas.agents.announcement_agent import AnnouncementAgent
from midas.models.market_event import EventType

# ---------------------------------------------------------------------------
# Sample TaiwanStockNews records (mimic FinMind API response)
# ---------------------------------------------------------------------------

_NEWS_FINANCIAL = {
    "date": "2024-05-10 08:30:00",
    "stock_id": "2330",
    "title": "台積電公告第一季EPS為8.7元",
    "link": "https://news.example.com/article/001",
    "source": "經濟日報",
    "description": "<p>詳細內容...</p>",
}

_NEWS_INVESTOR = {
    "date": "2024-05-10 10:00:00",
    "stock_id": "2330",
    "title": "台積電舉辦法說會說明未來展望",
    "link": "https://news.example.com/article/002",
    "source": "工商時報",
    "description": "<p>詳細內容...</p>",
}

_NEWS_MATERIAL = {
    "date": "2024-05-10 14:00:00",
    "stock_id": "2330",
    "title": "台積電宣布重大訊息：收購新廠",
    "link": "https://news.example.com/article/003",
    "source": "聯合報",
    "description": "<p>詳細內容...</p>",
}

_NEWS_GENERAL = {
    "date": "2024-05-10 16:00:00",
    "stock_id": "2330",
    "title": "台積電股價創新高",
    "link": "https://news.example.com/article/004",
    "source": "自由時報",
    "description": "<p>詳細內容...</p>",
}

_NEWS_NO_LINK = {
    "date": "2024-05-10 09:00:00",
    "stock_id": "2330",
    "title": "台積電最新動態",
    "link": "",
    "source": "鉅亨網",
    "description": "",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_stock_news.return_value = {
        "data": [_NEWS_FINANCIAL, _NEWS_INVESTOR, _NEWS_MATERIAL, _NEWS_GENERAL]
    }
    return client


@pytest.fixture
def agent(mock_client: MagicMock) -> AnnouncementAgent:
    return AnnouncementAgent(finmind_client=mock_client)


# ---------------------------------------------------------------------------
# Tests: fetch_announcements
# ---------------------------------------------------------------------------


def test_returns_empty_when_no_client() -> None:
    ag = AnnouncementAgent(finmind_client=None)
    assert ag.fetch_announcements("2330", "2024-05-10") == []


def test_returns_empty_when_api_raises(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.side_effect = RuntimeError("network error")
    ag = AnnouncementAgent(finmind_client=mock_client)
    result = ag.fetch_announcements("2330", "2024-05-10")
    assert result == []


def test_returns_empty_when_data_empty(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": []}
    ag = AnnouncementAgent(finmind_client=mock_client)
    assert ag.fetch_announcements("2330", "2024-05-10") == []


def test_returns_correct_count(agent: AnnouncementAgent) -> None:
    events = agent.fetch_announcements("2330", "2024-05-10")
    assert len(events) == 4


# ---------------------------------------------------------------------------
# Tests: field mapping
# ---------------------------------------------------------------------------


def test_title_mapped(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_FINANCIAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.title == _NEWS_FINANCIAL["title"]


def test_source_url_mapped(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_FINANCIAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.source_url == _NEWS_FINANCIAL["link"]


def test_source_name_mapped(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_FINANCIAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.source_name == _NEWS_FINANCIAL["source"]


def test_event_date_is_date_part_only(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_FINANCIAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.event_date == "2024-05-10"


def test_occurred_at_is_parsed_datetime(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_FINANCIAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert isinstance(event.occurred_at, datetime)
    assert event.occurred_at == datetime(2024, 5, 10, 16, 30, 0)


def test_occurred_at_parses_iso_z_and_converts_to_taipei(mock_client: MagicMock) -> None:
    news_z = dict(_NEWS_FINANCIAL)
    news_z["date"] = "2024-05-10T10:20:00Z"
    mock_client.get_stock_news.return_value = {"data": [news_z]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.occurred_at == datetime(2024, 5, 10, 18, 20, 0)


def test_occurred_at_shifts_source_time_by_eight_hours(mock_client: MagicMock) -> None:
    news_taipei = dict(_NEWS_FINANCIAL)
    news_taipei["date"] = "2026-05-22 01:04:00"
    mock_client.get_stock_news.return_value = {"data": [news_taipei]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2026-05-22")[0]
    assert event.occurred_at == datetime(2026, 5, 22, 9, 4, 0)


def test_symbol_set_correctly(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_FINANCIAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.symbol == "2330"


def test_fallback_source_url_when_link_empty(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_NO_LINK]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.source_url  # must not be empty
    assert "2330" in event.source_url


# ---------------------------------------------------------------------------
# Tests: event type classification
# ---------------------------------------------------------------------------


def test_financial_report_classification(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_FINANCIAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.event_type == EventType.FINANCIAL_REPORT


def test_investor_conference_classification(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_INVESTOR]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.event_type == EventType.INVESTOR_CONFERENCE


def test_material_news_classification(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_MATERIAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.event_type == EventType.MATERIAL_NEWS


def test_general_announcement_classification(mock_client: MagicMock) -> None:
    mock_client.get_stock_news.return_value = {"data": [_NEWS_GENERAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    event = ag.fetch_announcements("2330", "2024-05-10")[0]
    assert event.event_type == EventType.GENERAL_ANNOUNCEMENT


# ---------------------------------------------------------------------------
# Tests: resilience — bad record skipped, rest returned
# ---------------------------------------------------------------------------


def test_bad_record_skipped_rest_returned(mock_client: MagicMock) -> None:
    bad_record = {"date": "invalid-date-format!!!!", "title": "", "link": "", "source": ""}
    mock_client.get_stock_news.return_value = {"data": [bad_record, _NEWS_GENERAL]}
    ag = AnnouncementAgent(finmind_client=mock_client)
    # bad record falls back gracefully (occurred_at uses datetime.now()); still returns both
    events = ag.fetch_announcements("2330", "2024-05-10")
    # at least the good record must be returned
    assert any(e.title == _NEWS_GENERAL["title"] for e in events)
