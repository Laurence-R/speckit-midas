"""MarketService: retrieves the latest market overview snapshot."""
from __future__ import annotations

from typing import Optional

from midas.models.market_overview import MarketOverview
from midas.repositories.interfaces import IMarketOverviewRepository
from midas.services.interfaces import IMarketService


class MarketService(IMarketService):
    """Provides the latest market overview snapshot from the repository."""

    def __init__(self, repo: IMarketOverviewRepository) -> None:
        self._repo = repo

    def get_today_overview(self) -> Optional[MarketOverview]:
        return self._repo.get_latest()
