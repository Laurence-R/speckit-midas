"""TWSEClient: wraps TWSE OpenAPI (openapi.twse.com.tw).

No API key required. Data is published with a 1-day lag after market close.
"""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://openapi.twse.com.tw/v1"
_TIMEOUT = 15


def roc_to_iso(roc_date: str) -> str:
    """Convert ROC date string 'YYYMMDD' → ISO 'YYYY-MM-DD'.

    e.g. ``"1150519"`` → ``"2026-05-19"``  (ROC year = Gregorian year − 1911)
    """
    s = roc_date.strip()
    if len(s) == 7 and s.isdigit():
        year = int(s[:3]) + 1911
        return f"{year}-{s[3:5]}-{s[5:7]}"
    return s  # fallback: return as-is


class TWSEClient:
    """HTTP client for the TWSE OpenAPI.  No authentication required."""

    # Per-day cache for STOCK_DAY_ALL: iso_date -> {code: row}
    _stock_day_cache: dict[str, dict[str, dict]] = {}

    # ------------------------------------------------------------------ #
    # Public methods
    # ------------------------------------------------------------------ #

    def get_market_index(self) -> list[dict]:
        """``GET /exchangeReport/MI_INDEX`` — today's index closing prices.

        Returns list of dicts with Chinese keys:
        ``日期`` (YYYMMDD), ``指數``, ``收盤指數``, ``漲跌``, ``漲跌點數``, ``漲跌百分比``
        """
        return self._get("/exchangeReport/MI_INDEX")

    def get_stock_day_all(self, iso_date: str | None = None) -> list[dict]:
        """``GET /exchangeReport/STOCK_DAY_ALL`` — today's all listed stocks.

        Returns list of dicts with keys:
        ``Date`` (YYYMMDD), ``Code``, ``Name``, ``TradeVolume``, ``TradeValue``,
        ``OpeningPrice``, ``HighestPrice``, ``LowestPrice``,
        ``ClosingPrice``, ``Change``, ``Transaction``

        Results are cached by *iso_date* to avoid repeated network calls when
        querying multiple stocks on the same trading day.
        """
        cache_key = iso_date or "latest"
        if cache_key not in self._stock_day_cache:
            rows = self._get("/exchangeReport/STOCK_DAY_ALL")
            self._stock_day_cache[cache_key] = {r["Code"]: r for r in rows if "Code" in r}
        return list(self._stock_day_cache[cache_key].values())

    def lookup_stock(self, code: str, iso_date: str | None = None) -> dict | None:
        """Return the STOCK_DAY_ALL row for *code*, or ``None`` if not found."""
        cache_key = iso_date or "latest"
        if cache_key not in self._stock_day_cache:
            self.get_stock_day_all(iso_date)
        return self._stock_day_cache.get(cache_key, {}).get(code)

    @staticmethod
    def roc_to_iso(roc_date: str) -> str:
        return roc_to_iso(roc_date)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get(self, path: str) -> list[dict]:
        url = _BASE_URL + path
        try:
            resp = requests.get(url, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("TWSEClient: GET %s failed: %s", path, exc)
            raise
