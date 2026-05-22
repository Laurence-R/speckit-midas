"""Unit tests for GeminiClient daily quota enforcement."""
from __future__ import annotations

import sqlite3
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from midas.exceptions import LLMQuotaExceededError
from midas.integrations.gemini_client import DAILY_CALL_LIMIT, GeminiClient
from midas.repositories.database import DatabaseManager


@pytest.fixture()
def db_conn() -> sqlite3.Connection:
    """In-memory DB with app_settings pre-populated."""
    mgr = DatabaseManager(db_path=":memory:")
    mgr.init()
    return mgr.connect()


@pytest.fixture()
def client(db_conn: sqlite3.Connection) -> GeminiClient:
    """Return a GeminiClient wired to an in-memory DB (no real API key)."""
    c = GeminiClient.__new__(GeminiClient)
    c._db_conn = db_conn
    # Stub out the generative client so no real API calls happen
    c._genai = MagicMock()
    c._genai.models.generate_content.return_value = MagicMock(text='{"events": []}')
    return c


# ---------------------------------------------------------------------------
# Quota enforcement
# ---------------------------------------------------------------------------

class TestDailyQuotaEnforcement:
    def test_call_succeeds_within_limit(self, client: GeminiClient) -> None:
        client._write_quota(DAILY_CALL_LIMIT - 1, str(date.today()))
        # Should not raise
        client.generate("sys", "user text")

    def test_raises_at_limit(self, client: GeminiClient) -> None:
        client._write_quota(DAILY_CALL_LIMIT, str(date.today()))
        with pytest.raises(LLMQuotaExceededError):
            client.generate("sys", "user text")

    def test_51st_call_raises(self, client: GeminiClient) -> None:
        """The 51st call in a day must raise LLMQuotaExceededError."""
        client._write_quota(DAILY_CALL_LIMIT, str(date.today()))
        with pytest.raises(LLMQuotaExceededError):
            client.generate("sys", "51st call")

    def test_count_increments_on_success(self, client: GeminiClient) -> None:
        client._write_quota(0, str(date.today()))
        client.generate("sys", "test")
        calls, _ = client._read_quota_with_date()
        assert calls == 1

    def test_quota_reset_on_new_day(self, client: GeminiClient) -> None:
        """If llm_daily_date is yesterday, the counter should reset to 1."""
        client._write_quota(DAILY_CALL_LIMIT, "2000-01-01")  # old date
        client.generate("sys", "new day call")  # should NOT raise
        calls, recorded = client._read_quota_with_date()
        assert recorded == str(date.today())
        assert calls == 1

    def test_get_daily_usage(self, client: GeminiClient) -> None:
        client._write_quota(5, str(date.today()))
        calls, _ = client.get_daily_usage()
        assert calls == 5
