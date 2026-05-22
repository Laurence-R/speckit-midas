"""Load fixture data into the local SQLite database for manual acceptance testing."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow running as a script from project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from midas.config import load_config
from midas.models.financial_metric import Direction, FinancialMetric, MetricType
from midas.models.market_event import EventType, MarketEvent, Sentiment
from midas.models.market_overview import MarketOverview
from midas.models.tracked_stock import TrackedStock
from midas.repositories.database import DatabaseManager
from midas.repositories.financial_metric_repo import FinancialMetricRepo
from midas.repositories.market_event_repo import MarketEventRepo
from midas.repositories.market_overview_repo import MarketOverviewRepo
from midas.repositories.tracked_stock_repo import TrackedStockRepo

STOCKS = [
    ("2330", "台積電"),
    ("2317", "鴻海"),
    ("2454", "聯發科"),
]

TODAY = datetime.now().strftime("%Y-%m-%d")
NOW = datetime.now()


def load_tracked_stocks(repo: TrackedStockRepo) -> None:
    for symbol, name in STOCKS:
        repo.add(TrackedStock(
            symbol=symbol,
            company_name=name,
            added_at=NOW,
            memo="",
            sort_order=0,
        ))
    print(f"  追蹤股: {len(STOCKS)} 檔")


def load_market_events(repo: MarketEventRepo) -> None:
    events: list[MarketEvent] = []
    for i, (symbol, company) in enumerate(STOCKS):
        # 3 events per stock
        events.append(MarketEvent(
            symbol=symbol,
            event_date=TODAY,
            event_type=EventType.FINANCIAL_REPORT,
            occurred_at=NOW - timedelta(hours=2),
            title=f"{company} 公告 {TODAY[:7]} 財務報告",
            source_url=f"https://news.finmindtrade.com/{symbol}/financial",
            source_name="FinMind",
            fetched_at=NOW,
            ai_summary="公司財報顯示本季營收和每股盈餘均符合市場預期，毛利率維持穩定水準。" * 2,
            sentiment=Sentiment.POSITIVE,
            ai_summary_generated_at=NOW,
        ))
        events.append(MarketEvent(
            symbol=symbol,
            event_date=TODAY,
            event_type=EventType.INVESTOR_CONFERENCE,
            occurred_at=NOW - timedelta(hours=1),
            title=f"{company} 舉辦法人說明會",
            source_url=f"https://news.finmindtrade.com/{symbol}/conference",
            source_name="FinMind",
            fetched_at=NOW,
        ))
        events.append(MarketEvent(
            symbol=symbol,
            event_date=TODAY,
            event_type=EventType.GENERAL_ANNOUNCEMENT,
            occurred_at=NOW - timedelta(minutes=30),
            title=f"{company} 一般公告事項",
            source_url=f"https://news.finmindtrade.com/{symbol}/general",
            source_name="FinMind",
            fetched_at=NOW,
        ))
    repo.upsert_many(events)
    print(f"  市場事件: {len(events)} 筆")


def load_financial_metrics(repo: FinancialMetricRepo) -> None:
    metrics: list[FinancialMetric] = []
    # Monthly periods (8 months): 2025-05 ~ 2026-04 → backwards
    from datetime import date
    base = date(2026, 4, 1)
    periods = []
    for i in range(8):
        m = base.month - i
        y = base.year
        while m <= 0:
            m += 12
            y -= 1
        periods.append(f"{y}-{m:02d}")
    periods = list(reversed(periods))  # chronological order

    values_by_type: dict[MetricType, list[float]] = {
        MetricType.PER: [18.0, 17.5, 18.2, 19.0, 20.1, 21.3, 22.0, 21.8],
        MetricType.PBR: [5.2, 5.0, 5.1, 5.3, 5.6, 5.8, 6.0, 5.9],
        MetricType.DIVIDEND_YIELD: [2.1, 2.0, 2.2, 2.3, 2.4, 2.5, 2.6, 2.5],
        MetricType.MONTHLY_REVENUE: [1800.0, 1750.0, 1820.0, 1900.0, 1950.0, 2000.0, 2050.0, 2100.0],
        MetricType.REVENUE_YOY: [8.0, 7.5, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0],
    }
    for symbol, _ in STOCKS:
        for metric_type, vals in values_by_type.items():
            for j, period in enumerate(periods):
                metrics.append(FinancialMetric(
                    symbol=symbol,
                    metric_type=metric_type,
                    period=period,
                    value=vals[j],
                    is_unreported=False,
                    source_name="FinMind",
                    fetched_at=NOW,
                    direction=Direction.IMPROVING if j > 0 else None,
                    change_pct=6.0 if j > 0 else None,
                ))
    repo.upsert_many(metrics)
    print(f"  財務指標: {len(metrics)} 筆")


def load_market_overview(repo: MarketOverviewRepo) -> None:
    overview = MarketOverview(
        trading_date=TODAY,
        taiex_close=21500.0,
        taiex_change=150.0,
        taiex_change_pct=0.70,
        volume_b=2500.0,
        volume_5d_avg_b=2300.0,
        sector_rankings=[
            {"rank": 1, "name": "半導體", "change_pct": 1.2, "direction": "up"},
            {"rank": 2, "name": "電子零組件", "change_pct": 0.8, "direction": "up"},
            {"rank": 3, "name": "金融", "change_pct": 0.3, "direction": "up"},
            {"rank": 4, "name": "鋼鐵", "change_pct": -0.5, "direction": "down"},
            {"rank": 5, "name": "航運", "change_pct": -1.0, "direction": "down"},
        ],
        institutional={
            "foreign_investor_net": 15_000_000_000,
            "investment_trust_net": -2_000_000_000,
            "dealer_net": 500_000_000,
        },
        source_name="FinMind",
        fetched_at=NOW,
    )
    repo.upsert(overview)
    print("  大盤總覽: 1 筆")


def main() -> None:
    config = load_config()
    db = DatabaseManager(db_path=str(config.db_path))
    db.init()
    conn = db.connect()

    print(f"載入測試資料至 {config.db_path}")
    try:
        load_tracked_stocks(TrackedStockRepo(conn))
        load_market_events(MarketEventRepo(conn))
        load_financial_metrics(FinancialMetricRepo(conn))
        load_market_overview(MarketOverviewRepo(conn))
        conn.commit()
        print("完成！")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
