"""HolidayCalendar: TWSE trading-day checker backed by FinMind TaiwanStockTradingDate."""
from __future__ import annotations

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class HolidayCalendar:
    """Checks whether a given date is a TWSE trading day.

    Fetches the official trading-date list from FinMind (TaiwanStockTradingDate)
    covering the previous year through the current year so that lookbacks across
    year boundaries work correctly.

    If the API call fails the calendar falls back to a conservative weekend-only
    check so that updates are never silently blocked by a transient network error.

    Parameters
    ----------
    finmind_client:
        Optional FinMindClient instance.  When omitted the calendar operates in
        fallback (weekend-only) mode; the client can be supplied later via
        ``set_client()``.
    """

    def __init__(self, finmind_client=None) -> None:
        self._trading_set: set[str] = set()
        self._loaded = False
        if finmind_client is not None:
            self._load_trading_dates(finmind_client)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def set_client(self, finmind_client) -> None:
        """Load trading dates using *finmind_client* (call once after DI wiring)."""
        if not self._loaded:
            self._load_trading_dates(finmind_client)

    def is_trading_day(self, check_date: str | None = None) -> bool:
        """Return True if *check_date* (YYYY-MM-DD, default today) is a trading day."""
        target = date.fromisoformat(check_date) if check_date else date.today()

        if self._loaded:
            return str(target) in self._trading_set

        # Fallback: weekend-only check when trading-date list is unavailable
        return target.weekday() < 5  # 0–4 = Mon–Fri

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load_trading_dates(self, finmind_client) -> None:
        today = date.today()
        # Cover prev-year through current year so year-end lookbacks work
        start = date(today.year - 1, 1, 1)
        # Request a bit beyond today for any pre-published future dates
        end = today + timedelta(days=30)
        try:
            dates = finmind_client.get_trading_dates(str(start), str(end))
            self._trading_set = set(dates)
            self._loaded = True
            logger.info(
                "HolidayCalendar: loaded %d trading dates (%s → %s)",
                len(self._trading_set),
                start,
                end,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "HolidayCalendar: failed to load trading dates: %s — fallback to weekend-only",
                exc,
            )
            self._trading_set = set()
            self._loaded = False
