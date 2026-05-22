"""Custom exceptions for the Midas application."""
from __future__ import annotations


class MidasError(Exception):
    """Base exception for all Midas-specific errors."""


class DataFetchError(MidasError):
    """External API or scraping failure."""

    def __init__(self, source: str, reason: str, retryable: bool = True) -> None:
        super().__init__(f"[{source}] {reason}")
        self.source = source
        self.reason = reason
        self.retryable = retryable


class LLMQuotaExceededError(MidasError):
    """Daily LLM call limit (50) has been reached."""


class CacheExpiredError(MidasError):
    """Cached data exists but is older than the configured TTL."""


class WatchlistLimitError(MidasError):
    """Attempt to add a stock when the watchlist already contains 30 entries."""
