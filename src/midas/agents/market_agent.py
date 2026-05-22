"""MarketAgent: fetches market overview and stock info.

Data sources
------------
* TAIEX / sector indices : TWSE OpenAPI  (openapi.twse.com.tw)  — free, no key
* Institutional flows    : FinMind       (finmindtrade.com)     — free register tier
* Stock prices           : TWSE OpenAPI  STOCK_DAY_ALL          — free, no key
* Stock meta             : FinMind       TaiwanStockInfo        — free register tier
"""
from __future__ import annotations

import logging
from datetime import datetime

from midas.agents.interfaces import IMarketAgent
from midas.integrations.finmind_client import FinMindClient
from midas.integrations.twse_client import TWSEClient, roc_to_iso
from midas.models.market_overview import MarketOverview

logger = logging.getLogger(__name__)

# Pattern suffix that marks a sector (類股) index entry
_SECTOR_SUFFIX = "類指數"
# Suffix we strip when displaying sector names
_DISPLAY_STRIP = "類指數"


def _parse_number(s: str) -> float:
    """Convert a localised number string to float, e.g. '1,234.56' → 1234.56.

    Returns 0.0 if the string is empty, '--', or not parseable.
    """
    cleaned = s.strip().replace(",", "")
    if not cleaned or cleaned in ("--", "－"):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class MarketAgent(IMarketAgent):
    """Fetches TWSE index, institutional flows, and sector rankings."""

    def __init__(
        self,
        finmind_client: FinMindClient | None = None,
        twse_client: TWSEClient | None = None,
    ) -> None:
        self._client = finmind_client or FinMindClient()
        self._twse = twse_client or TWSEClient()

    def fetch_overview(self, trading_date: str) -> MarketOverview:
        """Fetch market overview for *trading_date*.

        TAIEX close + volume : FinMind TaiwanStockPrice (stock_id='TAIEX')
        Institutional flows  : FinMind TaiwanStockTotalInstitutionalInvestors
        Sector rankings      : TWSE OpenAPI MI_INDEX (best-effort; empty on failure)
        """
        # ---- TAIEX daily from FinMind (close, change, volume) ----
        try:
            taiex_raw = self._client.get_taiex_daily(trading_date)
        except Exception as exc:
            logger.warning("MarketAgent: get_taiex_daily failed for %s: %s", trading_date, exc)
            raise

        taiex_records = taiex_raw.get("data", [])
        if taiex_records:
            rec = taiex_records[0]
            taiex_close = float(rec.get("close", 0))
            taiex_change = float(rec.get("spread", 0))  # signed point change
            prev_close = taiex_close - taiex_change
            change_pct = round(taiex_change / prev_close * 100, 2) if prev_close else 0.0
            # Trading_money is in NTD; divide by 1e8 for 億元
            volume_b = round(float(rec.get("Trading_money", 0)) / 1e8, 1)
        else:
            taiex_close = 0.0
            taiex_change = 0.0
            change_pct = 0.0
            volume_b = 0.0

        # ---- Sector rankings from TWSE MI_INDEX (best-effort) ----
        sectors: list[dict] = []
        try:
            index_rows = self._twse.get_market_index()
            for r in index_rows:
                index_name = r.get("指數", "").strip()
                if not index_name.endswith(_SECTOR_SUFFIX):
                    continue
                if "報酬" in index_name:
                    continue
                display = index_name[: -len(_DISPLAY_STRIP)]
                pct = _parse_number(r.get("漲跌百分比", "0"))
                sectors.append({"name": display, "change_pct": pct})
            sectors.sort(key=lambda x: x["change_pct"], reverse=True)
            for i, s in enumerate(sectors, start=1):
                s["rank"] = i
                s["direction"] = "up" if s["change_pct"] >= 0 else "down"
        except Exception as exc:
            logger.warning("MarketAgent: TWSE sector rankings unavailable: %s", exc)

        # ---- Institutional flows from FinMind ----
        try:
            inst_raw = self._client.get_institutional_investors(trading_date)
        except Exception as exc:
            logger.warning("MarketAgent: get_institutional_investors failed for %s: %s", trading_date, exc)
            inst_raw = {"data": []}
        inst_list = inst_raw.get("data", [])
        foreign_net = 0.0
        trust_net = 0.0
        dealer_net = 0.0
        for r in inst_list:
            name = r.get("name", "")
            net = (float(r.get("buy", 0)) - float(r.get("sell", 0))) / 1e8  # 億
            if name == "Foreign_Investor":
                foreign_net = net
            elif name == "Investment_Trust":
                trust_net = net
            elif name in ("Dealer_self", "Dealer_Hedging"):
                dealer_net += net

        return MarketOverview(
            trading_date=trading_date,
            taiex_close=taiex_close,
            taiex_change=taiex_change,
            taiex_change_pct=round(change_pct, 2),
            volume_b=round(volume_b, 1),
            sector_rankings=sectors,
            institutional={
                "foreign_investor_net": foreign_net,
                "investment_trust_net": trust_net,
                "dealer_net": dealer_net,
            },
            source_name="FinMind",
            fetched_at=datetime.now(),
        )

    def get_stock_info(self, symbol: str) -> dict:
        """Return basic info dict for a symbol."""
        try:
            raw = self._client.get_stock_info(symbol)
            # FinMindClient.get_stock_info() returns a flat dict (row.iloc[0].to_dict())
            return {
                "symbol": symbol,
                "company_name": raw.get("stock_name", symbol),
                "industry": raw.get("industry_category", ""),
            }
        except Exception as exc:
            logger.warning("MarketAgent: get_stock_info failed for %s: %s", symbol, exc)
            return {"symbol": symbol, "company_name": symbol, "industry": ""}

    def get_latest_price(self, symbol: str, trading_date: str) -> dict | None:
        """Fetch the latest close price for *symbol* via FinMind TaiwanStockPrice.

        Uses ``FinMindClient.get_stock_price()`` which calls
        ``DataLoader.taiwan_stock_daily`` under the hood.

        Returns a dict with keys: ``close``, ``open``, ``date``, ``change_pct``
        (or ``None`` if the symbol has no data for that day).
        """
        try:
            raw = self._client.get_stock_price(
                symbol, start_date=trading_date, end_date=trading_date
            )
            records = raw.get("data", [])
            if not records:
                logger.debug("MarketAgent: no FinMind price data for %s on %s", symbol, trading_date)
                return None

            rec = records[0]
            close = float(rec.get("close", 0))
            if not close:
                return None  # halted / no trade

            spread = float(rec.get("spread", 0))  # 漲跌點（有正負號）
            open_ = float(rec.get("open", 0))

            change_pct: float | None = None
            prev_close = close - spread
            if prev_close:
                change_pct = round(spread / prev_close * 100, 2)

            return {
                "close": close,
                "open": open_,
                "date": str(rec.get("date", trading_date)),
                "change_pct": change_pct,
            }
        except Exception as exc:
            logger.warning("MarketAgent: get_latest_price failed for %s: %s", symbol, exc)
            return None
