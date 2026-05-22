"""UpdateService: decides when to update and launches the background worker."""
from __future__ import annotations

import logging
import queue
from datetime import datetime, timedelta

from midas.repositories.interfaces import IAppSettingRepository, IUpdateJobRepository
from midas.services.interfaces import IUpdateService
from midas.utils.holiday_calendar import HolidayCalendar

logger = logging.getLogger(__name__)

_UPDATE_HOUR = 15  # 15:00 local time


class UpdateService(IUpdateService):
    """Determines whether a post-market update is needed and starts the pipeline."""

    def __init__(
        self,
        db_conn,  # sqlite3.Connection
        orchestrator,  # Orchestrator
        background_worker,  # BackgroundWorker
        app_setting_repo: IAppSettingRepository,
        job_repo: IUpdateJobRepository,
        result_queue: queue.Queue,
        holiday_calendar: HolidayCalendar | None = None,
        finmind_client=None,
    ) -> None:
        self._conn = db_conn
        self._orchestrator = orchestrator
        self._worker = background_worker
        self._app_settings = app_setting_repo
        self._job_repo = job_repo
        self._queue = result_queue
        self._calendar = holiday_calendar or HolidayCalendar()
        if finmind_client is not None:
            self._calendar.set_client(finmind_client)

    # ------------------------------------------------------------------
    # IUpdateService
    # ------------------------------------------------------------------

    def check_needs_update(self) -> bool:
        """True if today is a trading day, it's after 15:00, and we haven't updated yet."""
        today = datetime.now().strftime("%Y-%m-%d")

        if not self._calendar.is_trading_day(today):
            return False

        if datetime.now().hour < _UPDATE_HOUR:
            return False

        last_date = self._app_settings.get_value("last_update_date")
        return last_date != today

    def start_background_update(self) -> None:
        """Start the Orchestrator pipeline in a background thread."""
        symbols = self._get_watched_symbols()
        target_date = self._get_target_date()
        self._worker.start(self._orchestrator.run, symbols, target_date)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_target_date(self) -> str:
        """Return the target trading date for the current update run.

        Before 15:00 (market not yet closed today): walk back to the most
        recent trading day so the update fetches yesterday's post-market data.
        At/after 15:00: use today.
        """
        now = datetime.now()
        d = now.date()
        if now.hour < _UPDATE_HOUR:
            d -= timedelta(days=1)
            # Walk back past non-trading days (e.g. weekends / holidays)
            for _ in range(7):
                if self._calendar.is_trading_day(str(d)):
                    break
                d -= timedelta(days=1)
        return str(d)

    def _get_watched_symbols(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT symbol FROM tracked_stocks ORDER BY sort_order ASC, added_at ASC"
        ).fetchall()
        return [r["symbol"] for r in rows]
