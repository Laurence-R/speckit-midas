"""trading_date: shared helper for determining the effective market data date."""
from __future__ import annotations

from datetime import date, datetime, timedelta

# Taiwan Stock Exchange closes at 13:30; 15:00 is when post-market data
# (institutional investors, PER, etc.) is typically fully published.
_UPDATE_HOUR = 15


def get_effective_date() -> str:
    """Return the effective trading date for querying/displaying market data.

    Rules (mirrors UpdateService._get_target_date):
    - Before 15:00: today's market has not yet closed → use yesterday's date
      so the UI shows the most recently settled data.
    - At/after 15:00: post-market data for today is available → use today.

    Returns
    -------
    str
        Date string in ``YYYY-MM-DD`` format.

    Notes
    -----
    Weekend/holiday walkback is intentionally omitted here; that responsibility
    belongs to UpdateService._get_target_date() on the write side.  The UI
    simply queries for whatever date was stored by the last update run.  On
    Monday morning before 15:00 this will return Sunday, which will yield zero
    events — an acceptable limitation until HolidayCalendar is integrated.
    """
    now = datetime.now()
    if now.hour < _UPDATE_HOUR:
        return str(date.today() - timedelta(days=1))
    return str(date.today())
