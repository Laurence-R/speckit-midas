"""Orchestrator: 4-step post-market data update pipeline."""
from __future__ import annotations

import logging
import queue
from datetime import date

from midas.agents.announcement_agent import AnnouncementAgent
from midas.agents.financial_agent import FinancialAgent
from midas.agents.interfaces import IMarketAgent
from midas.models.update_job import JobStatus, UpdateJob
from midas.repositories.interfaces import (
    IAppSettingRepository,
    IFinancialMetricRepository,
    IMarketEventRepository,
    IMarketOverviewRepository,
    ITrackedStockRepository,
    IUpdateJobRepository,
)

logger = logging.getLogger(__name__)

_TOTAL_STEPS = 4


class Orchestrator:
    """Executes the 4-step post-market update pipeline."""

    def __init__(
        self,
        market_agent: IMarketAgent,
        announcement_agent: AnnouncementAgent,
        financial_agent: FinancialAgent,
        market_overview_repo: IMarketOverviewRepository,
        market_event_repo: IMarketEventRepository,
        financial_metric_repo: IFinancialMetricRepository,
        update_job_repo: IUpdateJobRepository,
        app_setting_repo: IAppSettingRepository,
        result_queue: queue.Queue,
        tracked_stock_repo: ITrackedStockRepository | None = None,
    ) -> None:
        self._market_agent = market_agent
        self._announcement_agent = announcement_agent
        self._financial_agent = financial_agent
        self._overview_repo = market_overview_repo
        self._event_repo = market_event_repo
        self._metric_repo = financial_metric_repo
        self._job_repo = update_job_repo
        self._app_settings = app_setting_repo
        self._queue = result_queue
        self._tracked_stock_repo = tracked_stock_repo

    def run(self, symbols: list[str], target_date: str | None = None) -> None:
        """Execute all 4 steps. Reports progress and completion via queue."""
        job = UpdateJob(total_steps=_TOTAL_STEPS)
        job_id = self._job_repo.create(job)
        job.id = job_id

        today = target_date or str(date.today())

        try:
            # Step 1: Market overview
            self._report_progress(1, "抓取大盤概況")
            overview = self._market_agent.fetch_overview(today)
            self._overview_repo.upsert(overview)
            # Step 1.5 (within Step 1): Update latest price for each tracked stock
            if self._tracked_stock_repo is not None:
                for symbol in symbols:
                    try:
                        price_info = self._market_agent.get_latest_price(symbol, today)
                        if price_info:
                            self._tracked_stock_repo.update_price(
                                symbol,
                                price_info["close"],
                                price_info.get("change_pct"),
                                price_info["date"],
                            )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Orchestrator price update failed for %s: %s", symbol, exc)
            job.completed_steps = 1

            # Step 2: Announcements for each symbol
            self._report_progress(2, "抓取公司公告")
            all_events = []
            for symbol in symbols:
                try:
                    events = self._announcement_agent.fetch_announcements(symbol, today)
                    all_events.extend(events)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Orchestrator Step 2 failed for %s: %s", symbol, exc)
            if all_events:
                self._event_repo.upsert_many(all_events)
            job.completed_steps = 2

            # Step 3: Financial metrics (always re-fetch to reflect latest data)
            self._report_progress(3, "更新財務指標")
            for symbol in symbols:
                try:
                    metrics = self._financial_agent.fetch_and_calculate(symbol)
                    if metrics:
                        self._metric_repo.upsert_many(metrics)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Orchestrator Step 3 failed for %s: %s", symbol, exc)
            job.completed_steps = 3

            # Step 4: Finalize
            self._report_progress(4, "完成更新")
            self._job_repo.complete(job_id, job.llm_calls_made)
            self._app_settings.set_value("last_update_date", today)
            job.completed_steps = 4
            job.status = JobStatus.SUCCESS
            self._queue.put(("update_complete", job))

        except Exception as exc:  # noqa: BLE001
            logger.exception("Orchestrator pipeline failed: %s", exc)
            self._job_repo.fail(job_id, str(exc))
            job.status = JobStatus.FAILED
            self._queue.put(("update_error", str(exc)))

    def _report_progress(self, step: int, label: str) -> None:
        self._queue.put(("progress", {"step": step, "total": _TOTAL_STEPS, "label": label}))
