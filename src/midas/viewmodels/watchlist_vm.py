"""WatchlistViewModel: wraps WatchlistService for the watchlist page."""
from __future__ import annotations

from midas.models.tracked_stock import TrackedStock
from midas.services.interfaces import IWatchlistService


class WatchlistViewModel:
    """Thin ViewModel wrapper for the watchlist page."""

    def __init__(self, watchlist_service: IWatchlistService) -> None:
        self._svc = watchlist_service

    def get_all(self) -> list[TrackedStock]:
        return self._svc.get_all()

    def add(self, symbol: str) -> TrackedStock:
        return self._svc.add(symbol)

    def remove(self, symbol: str) -> None:
        self._svc.remove(symbol)

    def update_memo(self, symbol: str, memo: str) -> None:
        self._svc.update_memo(symbol, memo)

    def search(self, query: str) -> list[TrackedStock]:
        return self._svc.search(query)
