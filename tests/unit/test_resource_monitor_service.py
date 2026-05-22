from __future__ import annotations

from datetime import datetime
from pathlib import Path

from midas.models.update_job import JobStatus, UpdateJob
from midas.repositories.app_setting_repo import AppSettingRepo
from midas.repositories.database import DatabaseManager
from midas.repositories.update_job_repo import UpdateJobRepo
from midas.services.resource_monitor_service import ResourceMonitorService


def test_get_snapshot_reads_repo_backed_monitor_data(tmp_path: Path) -> None:
    db_path = tmp_path / "midas.db"
    db = DatabaseManager(db_path=db_path)
    db.init()
    conn = db.connect()

    conn.execute(
        "INSERT INTO market_events(symbol, event_date, event_type, event_type_priority, occurred_at, title, source_url, source_name, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("2330", "2026-05-22", "material_news", 3, "2026-05-22T10:00:00", "新聞", "https://example.com/1", "FinMind", "2026-05-22T10:05:00"),
    )
    conn.execute(
        "INSERT INTO financial_metrics(symbol, metric_type, period, value, source_name, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("2330", "PER", "2026-Q1", 18.5, "FinMind", "2026-05-22T10:05:00"),
    )
    conn.execute(
        "INSERT INTO market_overviews(trading_date, taiex_close, taiex_change, taiex_change_pct, volume_b, sector_rankings, institutional, source_name, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("2026-05-22", 21000.0, 100.0, 0.48, 2500.0, "[]", "{}", "FinMind", "2026-05-22T15:10:00"),
    )
    conn.commit()

    app_settings = AppSettingRepo(conn)
    app_settings.set_value("gemini_api_key", "test-key")

    job_repo = UpdateJobRepo(conn)
    job_id = job_repo.create(UpdateJob(total_steps=4, triggered_at=datetime(2026, 5, 22, 15, 30)))
    job_repo.complete(job_id)

    service = ResourceMonitorService(
        conn=conn,
        app_setting_repo=app_settings,
        update_job_repo=job_repo,
        db_path=db_path,
    )

    snapshot = service.get_snapshot()

    assert snapshot.has_gemini_key is True
    assert snapshot.last_success_at == datetime(2026, 5, 22, 15, 30)
    assert snapshot.market_event_count == 1
    assert snapshot.financial_metric_count == 1
    assert snapshot.market_overview_count == 1
    assert snapshot.db_size_mb is not None


def test_get_snapshot_handles_missing_success_job(tmp_path: Path) -> None:
    db_path = tmp_path / "midas.db"
    db = DatabaseManager(db_path=db_path)
    db.init()
    conn = db.connect()

    service = ResourceMonitorService(
        conn=conn,
        app_setting_repo=AppSettingRepo(conn),
        update_job_repo=UpdateJobRepo(conn),
        db_path=db_path,
    )

    snapshot = service.get_snapshot()

    assert snapshot.has_gemini_key is False
    assert snapshot.last_success_at is None
    assert snapshot.market_event_count == 0
    assert snapshot.financial_metric_count == 0
    assert snapshot.market_overview_count == 0
    assert snapshot.db_size_mb is not None