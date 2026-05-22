"""FinMind client using the official FinMind Python library (DataLoader)."""
from __future__ import annotations

import logging
from typing import Any

from midas.config import AppConfig
from midas.exceptions import DataFetchError

logger = logging.getLogger(__name__)

# Hard limit: abort the update round when accumulated requests reach this number
_REQUEST_ABORT_LIMIT = 800


class FinMindClient:
    """Wrapper around FinMind.data.DataLoader with token auth and rate limiting.

    Uses the official FinMind Python library so authentication is handled
    correctly (login_by_token) and all datasets available to the user's
    subscription level are accessible.
    """

    def __init__(self, config: AppConfig | None = None, db_conn=None) -> None:
        from FinMind.data import DataLoader

        if config is None:
            from midas.config import load_config
            config = load_config()

        self._token: str = config.finmind_token
        self._db_conn = db_conn
        self._request_count: int = 0
        self._api = DataLoader()
        self._applied_token: str = ""
        self._apply_token()

    # ------------------------------------------------------------------
    # Public API methods  (interface kept identical to original)
    # ------------------------------------------------------------------

    def get_taiex_daily(self, date: str) -> dict[str, Any]:
        """Fetch TAIEX daily OHLCV from TaiwanStockPrice (stock_id='TAIEX').

        Returns a single-record dict with keys:
          close, open, max, min, spread (point change), Trading_money (NTD).
        """
        self._ensure_token()
        self._check_quota()
        try:
            df = self._api.taiwan_stock_daily(
                stock_id="TAIEX", start_date=date, end_date=date
            )
            self._request_count += 1
            if df.empty:
                return {"data": []}
            return {"data": df.to_dict("records")}
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def get_institutional_investors(self, date: str) -> dict[str, Any]:
        """Fetch market-wide institutional investor totals (TaiwanStockTotalInstitutionalInvestors)."""
        self._ensure_token()
        self._check_quota()
        try:
            df = self._api.taiwan_stock_institutional_investors_total(
                start_date=date, end_date=date
            )
            self._request_count += 1
            return {"data": df.to_dict("records")}
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def get_stock_price(
        self, symbol: str, start_date: str, end_date: str | None = None
    ) -> dict[str, Any]:
        """Fetch daily OHLCV price data for *symbol* (TaiwanStockPrice)."""
        self._ensure_token()
        self._check_quota()
        try:
            df = self._api.taiwan_stock_daily(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date or "",
            )
            self._request_count += 1
            return {"data": df.to_dict("records")}
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def get_institutional_investors_by_stock(
        self, symbol: str, start_date: str, end_date: str | None = None
    ) -> dict[str, Any]:
        """Fetch per-stock institutional investor buy/sell (TaiwanStockInstitutionalInvestorsBuySell)."""
        self._ensure_token()
        self._check_quota()
        try:
            df = self._api.taiwan_stock_institutional_investors(
                stock_id=symbol,
                start_date=start_date,
                end_date=end_date or "",
            )
            self._request_count += 1
            return {"data": df.to_dict("records")}
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def get_per_pbr(self, symbol: str, start_date: str) -> dict[str, Any]:
        """Fetch daily PER / PBR / dividend yield for *symbol* (TaiwanStockPER)."""
        self._ensure_token()
        self._check_quota()
        try:
            df = self._api.taiwan_stock_per_pbr(
                stock_id=symbol, start_date=start_date
            )
            self._request_count += 1
            return {"data": df.to_dict("records")}
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def get_monthly_revenue(self, symbol: str, start_date: str) -> dict[str, Any]:
        """Fetch monthly revenue for *symbol* (TaiwanStockMonthRevenue)."""
        self._ensure_token()
        self._check_quota()
        try:
            df = self._api.taiwan_stock_month_revenue(
                stock_id=symbol, start_date=start_date
            )
            self._request_count += 1
            return {"data": df.to_dict("records")}
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def get_trading_dates(self, start_date: str, end_date: str) -> list[str]:
        """Return a list of TWSE trading dates (YYYY-MM-DD) in [start_date, end_date]."""
        self._ensure_token()
        try:
            df = self._api.taiwan_stock_trading_date(
                start_date=start_date, end_date=end_date
            )
            self._request_count += 1
            if df.empty or "date" not in df.columns:
                return []
            return df["date"].tolist()
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def get_stock_info(self, symbol: str) -> dict[str, Any]:
        """Fetch basic stock information for *symbol* (TaiwanStockInfo)."""
        self._ensure_token()
        self._check_quota()
        try:
            df = self._api.taiwan_stock_info()
            self._request_count += 1
            if df.empty or "stock_id" not in df.columns:
                raise DataFetchError(
                    source="FinMind",
                    reason=f"No stock info found for symbol '{symbol}'",
                    retryable=False,
                )
            row = df[df["stock_id"] == symbol]
            if row.empty:
                raise DataFetchError(
                    source="FinMind",
                    reason=f"No stock info found for symbol '{symbol}'",
                    retryable=False,
                )
            return row.iloc[0].to_dict()
        except DataFetchError:
            raise
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def get_stock_news(self, symbol: str, date: str) -> dict[str, Any]:
        """Fetch news articles for *symbol* on/after *date* (TaiwanStockNews).

        Uses the FinMind REST API directly (no DataLoader method available).
        Returns {"data": [{title, link, source, date, stock_id, description}, ...]}
        """
        import requests  # noqa: PLC0415

        self._ensure_token()
        self._check_quota()
        try:
            resp = requests.get(
                "https://api.finmindtrade.com/api/v4/data",
                params={"dataset": "TaiwanStockNews", "data_id": symbol, "start_date": date},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30,
            )
            self._request_count += 1
            if resp.status_code != 200:
                raise DataFetchError(
                    source="FinMind",
                    reason=f"TaiwanStockNews HTTP {resp.status_code}: {resp.text[:200]}",
                    retryable=True,
                )
            records = resp.json().get("data", [])
            logger.info("FinMindClient.get_stock_news(%s, %s): %d records", symbol, date, len(records))
            return {"data": records}
        except DataFetchError:
            raise
        except Exception as exc:
            raise DataFetchError(source="FinMind", reason=str(exc), retryable=True) from exc

    def reset_request_count(self) -> None:
        """Reset the in-round request counter (call at the start of each update round)."""
        self._request_count = 0

    def get_request_count(self) -> int:
        """Return the number of API requests made in the current update round."""
        return self._request_count

    def get_api_usage(self) -> tuple[int, int]:
        """Return (current_usage, usage_limit) as reported by the FinMind server.

        To avoid stale values across multiple FinMindClient instances (foreground
        monitor vs background updater), this method refreshes usage metadata by
        re-authenticating with the current token before reading ``api_usage``.
        Returns (0, 600) when the token is not set or values are unavailable.
        """
        try:
            self._refresh_token_from_db()
            if not self._token:
                return 0, 600

            # Force refresh so usage reflects server-side latest state even when
            # requests were made by another FinMindClient instance.
            self._api.login_by_token(api_token=self._token)
            self._applied_token = self._token

            usage = int(self._api.api_usage or 0)
            limit = int(self._api.api_usage_limit or 600)
            return usage, limit
        except Exception:
            return 0, 600

    def has_token(self) -> bool:
        """Return True if a non-empty FinMind token is currently configured."""
        self._refresh_token_from_db()
        return bool(self._token)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _refresh_token_from_db(self) -> None:
        """Re-read FinMind token from DB so settings-page saves take effect immediately.

        Accepts an empty string from the DB so that clearing the token in the
        Settings page actually stops authenticated API calls.
        """
        db_conn = getattr(self, "_db_conn", None)
        if db_conn is None:
            return
        try:
            db_row = db_conn.execute(
                "SELECT value FROM app_settings WHERE key = 'finmind_token'"
            ).fetchone()
            if db_row is not None:  # row exists → always reflect DB value (even empty)
                self._token = db_row["value"] or ""
        except Exception:
            pass

    def _apply_token(self) -> None:
        """Call login_by_token if the token has changed; reset state when cleared."""
        if self._token and self._token != self._applied_token:
            self._api.login_by_token(api_token=self._token)
            self._applied_token = self._token
        elif not self._token:
            # Token was cleared — reset tracking so a later save picks it up correctly.
            self._applied_token = ""

    def _ensure_token(self) -> None:
        """Refresh token from DB then re-login if it changed."""
        self._refresh_token_from_db()
        self._apply_token()

    def _check_quota(self) -> None:
        """Raise DataFetchError(retryable=False) if the per-round request limit is hit."""
        if self._request_count >= _REQUEST_ABORT_LIMIT:
            raise DataFetchError(
                source="FinMind",
                reason=(
                    f"Per-round request limit reached ({_REQUEST_ABORT_LIMIT}). "
                    "Aborting update to protect daily quota."
                ),
                retryable=False,
            )
