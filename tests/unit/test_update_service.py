from __future__ import annotations

from unittest.mock import MagicMock, patch

from midas.services.update_service import UpdateService


def _make_service() -> tuple[UpdateService, MagicMock, MagicMock, MagicMock, MagicMock]:
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [{"symbol": "2330"}, {"symbol": "2317"}]
    orchestrator = MagicMock()
    worker = MagicMock()
    app_settings = MagicMock()
    job_repo = MagicMock()
    calendar = MagicMock()
    calendar.is_trading_day.return_value = True
    service = UpdateService(
        db_conn=conn,
        orchestrator=orchestrator,
        background_worker=worker,
        app_setting_repo=app_settings,
        job_repo=job_repo,
        result_queue=MagicMock(),
        holiday_calendar=calendar,
    )
    return service, conn, worker, app_settings, calendar


def test_check_needs_update_uses_app_setting_repo() -> None:
    service, _, _, app_settings, calendar = _make_service()
    app_settings.get_value.return_value = "2026-05-21"

    with patch("midas.services.update_service.datetime") as mock_datetime:
        now = MagicMock()
        now.strftime.return_value = "2026-05-22"
        now.hour = 16
        now.date.return_value = None
        mock_datetime.now.return_value = now

        assert service.check_needs_update() is True

    calendar.is_trading_day.assert_called_once_with("2026-05-22")
    app_settings.get_value.assert_called_once_with("last_update_date")


def test_start_background_update_launches_worker_without_callbacks() -> None:
    service, _, worker, _, _ = _make_service()

    with patch.object(service, "_get_target_date", return_value="2026-05-22"):
        service.start_background_update()

    worker.start.assert_called_once_with(service._orchestrator.run, ["2330", "2317"], "2026-05-22")