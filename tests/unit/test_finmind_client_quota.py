"""Unit tests for FinMindClient quota enforcement.

The new implementation uses FinMind.data.DataLoader — HTTP-level mocking is
no longer applicable.  These tests cover the quota counter and _check_quota().
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from midas.exceptions import DataFetchError
from midas.integrations.finmind_client import (
    FinMindClient,
    _REQUEST_ABORT_LIMIT,
)


@pytest.fixture()
def client() -> FinMindClient:
    """Return a FinMindClient whose DataLoader is replaced with a MagicMock."""
    c = FinMindClient.__new__(FinMindClient)
    c._token = "test-token"
    c._applied_token = "test-token"
    c._request_count = 0
    c._db_conn = None
    c._api = MagicMock()
    return c


# ---------------------------------------------------------------------------
# Quota enforcement
# ---------------------------------------------------------------------------

class TestQuotaEnforcement:
    def test_raises_when_limit_reached(self, client: FinMindClient) -> None:
        client._request_count = _REQUEST_ABORT_LIMIT
        with pytest.raises(DataFetchError) as exc_info:
            client._check_quota()
        assert exc_info.value.retryable is False
        assert "limit" in str(exc_info.value).lower()

    def test_does_not_raise_below_limit(self, client: FinMindClient) -> None:
        client._request_count = _REQUEST_ABORT_LIMIT - 1
        # Should not raise
        client._check_quota()

    def test_request_count_increments(self, client: FinMindClient) -> None:
        df = pd.DataFrame([{"stock_id": "2330", "stock_name": "台積電", "industry_category": "半導體"}])
        client._api.taiwan_stock_info.return_value = df
        client.get_stock_info("2330")
        assert client._request_count == 1

    def test_abort_at_exactly_800(self, client: FinMindClient) -> None:
        client._request_count = _REQUEST_ABORT_LIMIT
        with pytest.raises(DataFetchError) as exc_info:
            client.get_stock_info("2330")
        assert exc_info.value.retryable is False


# ---------------------------------------------------------------------------
# No stock found
# ---------------------------------------------------------------------------

class TestStockNotFound:
    def test_raises_on_empty_data(self, client: FinMindClient) -> None:
        import pandas as pd
        client._api.taiwan_stock_info.return_value = pd.DataFrame(columns=["stock_id", "stock_name"])
        with pytest.raises(DataFetchError) as exc_info:
            client.get_stock_info("9999")
        assert exc_info.value.retryable is False


# ---------------------------------------------------------------------------
# API usage metadata
# ---------------------------------------------------------------------------

class TestApiUsage:
    def test_get_api_usage_refreshes_login_and_reads_values(self, client: FinMindClient) -> None:
        client._api.api_usage = "96"
        client._api.api_usage_limit = "600"

        usage, limit = client.get_api_usage()

        client._api.login_by_token.assert_called_once_with(api_token="test-token")
        assert usage == 96
        assert limit == 600

    def test_get_api_usage_without_token_returns_defaults(self, client: FinMindClient) -> None:
        client._token = ""

        usage, limit = client.get_api_usage()

        client._api.login_by_token.assert_not_called()
        assert usage == 0
        assert limit == 600
