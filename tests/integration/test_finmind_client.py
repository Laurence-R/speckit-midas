"""Integration tests for FinMindClient against the real FinMind API.

Requires FINMIND_TOKEN environment variable to be set.
Skipped in CI if token is not present.

Run with:
    uv run pytest tests/integration/test_finmind_client.py -m integration
"""
from __future__ import annotations

import os

import pytest

from midas.config import load_config
from midas.integrations.finmind_client import FinMindClient


@pytest.fixture()
def client() -> FinMindClient:
    return FinMindClient(config=load_config())


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("FINMIND_TOKEN"),
    reason="FINMIND_TOKEN not set — skipping live API tests",
)
class TestFinMindClientLive:
    def test_get_stock_info_tsmc(self, client: FinMindClient) -> None:
        info = client.get_stock_info("2330")
        assert info.get("stock_id") == "2330"
        assert "stock_name" in info

    def test_get_per_pbr(self, client: FinMindClient) -> None:
        result = client.get_per_pbr("2330", "2024-01-01")
        assert "data" in result
        assert isinstance(result["data"], list)

    def test_get_monthly_revenue(self, client: FinMindClient) -> None:
        result = client.get_monthly_revenue("2330", "2024-01-01")
        assert "data" in result
        assert isinstance(result["data"], list)
