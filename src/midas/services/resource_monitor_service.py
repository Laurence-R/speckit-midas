"""Read-model service for the resource monitor page."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from midas.repositories.interfaces import IAppSettingRepository, IUpdateJobRepository


@dataclass(frozen=True)
class ResourceMonitorSnapshot:
    has_gemini_key: bool
    last_success_at: datetime | None
    market_event_count: int
    financial_metric_count: int
    market_overview_count: int
    db_size_mb: float | None


class ResourceMonitorService:
    """Aggregates read-only data needed by the resource monitor page."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        app_setting_repo: IAppSettingRepository,
        update_job_repo: IUpdateJobRepository,
        db_path: Path | None = None,
    ) -> None:
        self._conn = conn
        self._app_settings = app_setting_repo
        self._update_jobs = update_job_repo
        self._db_path = db_path

    def get_snapshot(self) -> ResourceMonitorSnapshot:
        latest_success = self._update_jobs.get_latest_success()
        return ResourceMonitorSnapshot(
            has_gemini_key=self._app_settings.has_value("gemini_api_key"),
            last_success_at=latest_success.triggered_at if latest_success else None,
            market_event_count=self._count_rows("market_events"),
            financial_metric_count=self._count_rows("financial_metrics"),
            market_overview_count=self._count_rows("market_overviews"),
            db_size_mb=self._get_db_size_mb(),
        )

    def _count_rows(self, table_name: str) -> int:
        row = self._conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return int(row[0]) if row else 0

    def _get_db_size_mb(self) -> float | None:
        if self._db_path is None or not Path(self._db_path).is_file():
            return None
        return os.path.getsize(self._db_path) / (1024 * 1024)