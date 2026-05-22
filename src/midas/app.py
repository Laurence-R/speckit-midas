"""Main application class: page routing, queue polling, update orchestration."""
from __future__ import annotations

import queue

import customtkinter as ctk

from midas.ui.app_window import AppWindow
from midas.ui.pages.dashboard_page import DashboardPage
from midas.ui.pages.settings_page import SettingsPage
from midas.ui.pages.stock_detail_page import StockDetailPage
from midas.ui.pages.resource_monitor_page import ResourceMonitorPage
from midas.ui.pages.watchlist_page import WatchlistPage

# Queue message keys
_MSG_PROGRESS = "progress"
_MSG_COMPLETE = "update_complete"
_MSG_ERROR = "update_error"


class App(ctk.CTk):
    """Top-level CTk application window."""

    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 800
    QUEUE_POLL_MS = 500

    def __init__(self) -> None:
        super().__init__()

        self.title("Midas — 台股盤後投研")
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.minsize(1024, 600)

        # Background update message queue
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()

        # Initialise DB + full dependency injection chain
        self._setup_dependencies()

        # Load saved font scale before building UI
        self._load_font_scale()

        # Build root layout
        self._window = AppWindow(self, on_navigate=self._navigate)
        self._window.pack(fill="both", expand=True)

        # Create all page frames (stacked inside content_area)
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._current_page: str = "dashboard"
        self._init_pages()

        # Wire status bar retry button
        self._window.status_bar.set_retry_command(self._start_update)

        # Show default page and immediately load data from DB
        self._navigate("dashboard")
        self._pages["dashboard"].load()

        # Show cached data timestamp in status bar
        import datetime
        _ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self._window.status_bar.show_ready(_ts + " (快取)")

        # Start queue polling
        self.after(self.QUEUE_POLL_MS, self._check_queue)

        # Trigger auto-update if today's post-market data is missing
        self.wire_update_service(self._update_service)

    # ------------------------------------------------------------------
    # Dependency Injection setup
    # ------------------------------------------------------------------

    def _setup_dependencies(self) -> None:
        """Initialise DB, create all repos / services / ViewModels."""
        from midas.config import load_config
        from midas.repositories.database import DatabaseManager

        config = load_config()
        db_mgr = self._init_database(config, DatabaseManager)
        self._build_foreground_dependencies(config)
        self._build_background_update_pipeline(config, db_mgr)

    def _init_database(self, config, database_manager_cls):
        db_mgr = database_manager_cls(db_path=str(config.db_path))
        db_mgr.init()
        self._conn = db_mgr.connect()
        # Sync tokens from env/.env into DB (first-run or .env-only setup).
        # This ensures the Settings page reflects whatever token is actually in use.
        self._sync_config_to_db(self._conn, config)
        return db_mgr

    def _build_foreground_dependencies(self, config) -> None:
        from midas.agents.market_agent import MarketAgent
        from midas.integrations.finmind_client import FinMindClient
        from midas.integrations.gemini_client import GeminiClient
        from midas.agents.summarization_agent import SummarizationAgent
        from midas.repositories.app_setting_repo import AppSettingRepo
        from midas.repositories.financial_metric_repo import FinancialMetricRepo
        from midas.repositories.market_event_repo import MarketEventRepo
        from midas.repositories.market_overview_repo import MarketOverviewRepo
        from midas.repositories.tracked_stock_repo import TrackedStockRepo
        from midas.repositories.update_job_repo import UpdateJobRepo
        from midas.services.event_service import EventService
        from midas.services.financial_service import FinancialService
        from midas.services.market_service import MarketService
        from midas.services.resource_monitor_service import ResourceMonitorService
        from midas.services.watchlist_service import WatchlistService
        from midas.viewmodels.dashboard_vm import DashboardViewModel
        from midas.viewmodels.stock_detail_vm import StockDetailViewModel
        from midas.viewmodels.watchlist_vm import WatchlistViewModel

        stock_repo = TrackedStockRepo(self._conn)
        self._app_setting_repo = AppSettingRepo(self._conn)
        event_repo = MarketEventRepo(self._conn)
        overview_repo = MarketOverviewRepo(self._conn)
        metric_repo = FinancialMetricRepo(self._conn)
        self._job_repo = UpdateJobRepo(self._conn)

        finmind = FinMindClient(config=config, db_conn=self._conn)
        self._finmind = finmind
        self._db_path = config.db_path

        market_agent = MarketAgent(finmind_client=finmind)
        market_svc = MarketService(overview_repo)
        event_svc = EventService(event_repo)
        financial_svc = FinancialService(metric_repo)
        self._resource_monitor_svc = ResourceMonitorService(
            conn=self._conn,
            app_setting_repo=self._app_setting_repo,
            update_job_repo=self._job_repo,
            db_path=config.db_path,
        )
        self._watchlist_svc = WatchlistService(stock_repo, market_agent)

        self._dashboard_vm = DashboardViewModel(market_svc, event_svc, self._watchlist_svc)
        self._stock_detail_vm = StockDetailViewModel(event_svc, financial_svc)
        self._watchlist_vm = WatchlistViewModel(self._watchlist_svc)

        gemini_fg = GeminiClient(config=config, db_conn=self._conn)
        self._summarization_agent = SummarizationAgent(gemini_client=gemini_fg)
        self._event_repo = event_repo

    def _build_background_update_pipeline(self, config, db_mgr) -> None:
        from midas.agents.announcement_agent import AnnouncementAgent
        from midas.agents.financial_agent import FinancialAgent
        from midas.agents.market_agent import MarketAgent
        from midas.agents.orchestrator import Orchestrator
        from midas.integrations.finmind_client import FinMindClient
        from midas.repositories.app_setting_repo import AppSettingRepo
        from midas.repositories.financial_metric_repo import FinancialMetricRepo
        from midas.repositories.market_event_repo import MarketEventRepo
        from midas.repositories.market_overview_repo import MarketOverviewRepo
        from midas.repositories.tracked_stock_repo import TrackedStockRepo
        from midas.repositories.update_job_repo import UpdateJobRepo
        from midas.services.update_service import UpdateService
        from midas.tasks.background_worker import BackgroundWorker

        # Background thread MUST use its own SQLite connection — SQLite connections
        # cannot be shared across threads.
        bg_conn = db_mgr.connect()
        bg_app_setting_repo = AppSettingRepo(bg_conn)
        finmind_bg = FinMindClient(config=config, db_conn=bg_conn)

        orchestrator = Orchestrator(
            market_agent=MarketAgent(finmind_client=finmind_bg),
            announcement_agent=AnnouncementAgent(finmind_client=finmind_bg),
            financial_agent=FinancialAgent(finmind_client=finmind_bg),
            market_overview_repo=MarketOverviewRepo(bg_conn),
            market_event_repo=MarketEventRepo(bg_conn),
            financial_metric_repo=FinancialMetricRepo(bg_conn),
            update_job_repo=UpdateJobRepo(bg_conn),
            app_setting_repo=bg_app_setting_repo,
            result_queue=self._queue,
            tracked_stock_repo=TrackedStockRepo(bg_conn),
        )
        self._update_service = UpdateService(
            db_conn=bg_conn,
            orchestrator=orchestrator,
            background_worker=BackgroundWorker(result_queue=self._queue),
            app_setting_repo=bg_app_setting_repo,
            job_repo=UpdateJobRepo(bg_conn),
            result_queue=self._queue,
            finmind_client=finmind_bg,
        )

    # ------------------------------------------------------------------
    # Startup helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sync_config_to_db(conn, config) -> None:
        """Write env-var API tokens to app_settings if the DB values are currently empty.

        This keeps the Settings page in sync with tokens supplied via .env or
        environment variables so the user can see and manage them from the UI.
        Only writes when the DB row is empty — never overwrites a value the user
        has already saved through the Settings page.
        """
        changed = False
        for key, value in [
            ("finmind_token", config.finmind_token),
            ("gemini_api_key", config.gemini_api_key),
        ]:
            if value:
                row = conn.execute(
                    "SELECT value FROM app_settings WHERE key = ?", (key,)
                ).fetchone()
                if row is not None and not row["value"]:
                    conn.execute(
                        "UPDATE app_settings"
                        " SET value = ?, updated_at = CURRENT_TIMESTAMP"
                        " WHERE key = ?",
                        (value, key),
                    )
                    changed = True
        if changed:
            conn.commit()

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def _init_pages(self) -> None:
        content = self._window.content_area
        pages = {
            "dashboard": DashboardPage(
                content,
                view_model=self._dashboard_vm,
                controller=self,
            ),
            "stock_detail": StockDetailPage(
                content,
                view_model=self._stock_detail_vm,
                summarization_agent=self._summarization_agent,
                event_repo=self._event_repo,
            ),
            "watchlist": WatchlistPage(
                content,
                view_model=self._watchlist_vm,
                controller=self,
            ),
            "resource_monitor": ResourceMonitorPage(
                content,
                monitor_service=self._resource_monitor_svc,
                finmind_client=self._finmind,
            ),
            "settings": SettingsPage(
                content,
                db_conn=self._conn,
                on_rebuild=self._rebuild_pages,
            ),
        }
        for name, frame in pages.items():
            frame.place(relwidth=1, relheight=1)
            self._pages[name] = frame

    def _navigate(self, page_name: str) -> None:
        """Raise *page_name* to the front of the content area."""
        frame = self._pages.get(page_name)
        if frame is None:
            return
        self._current_page = page_name
        frame.tkraise()
        self._window.sidebar.set_active(page_name)

    def show_frame(self, page_name: str, **kwargs: object) -> None:
        """Public method for navigating with optional parameters (e.g. symbol)."""
        frame = self._pages.get(page_name)
        if frame is None:
            return
        if kwargs and hasattr(frame, "load"):
            frame.load(**kwargs)
        frame.tkraise()
        self._window.sidebar.set_active(page_name)

    def show_stock_detail(self, symbol: str) -> None:
        """Controller callback: navigate to stock detail for *symbol*."""
        self.show_frame("stock_detail", symbol=symbol)

    def _load_font_scale(self) -> None:
        """Read saved font_scale from DB and apply it before UI is built."""
        from midas.ui.theme import set_font_scale
        try:
            value = self._app_setting_repo.get_value("font_scale")
            if value:
                set_font_scale(int(value))
        except Exception:
            pass

    def _rebuild_pages(self) -> None:
        """Destroy all page frames and recreate them (called after font scale change)."""
        for frame in list(self._pages.values()):
            frame.destroy()
        self._pages.clear()
        self._init_pages()
        self._navigate(self._current_page)
        dashboard = self._pages.get("dashboard")
        if dashboard and hasattr(dashboard, "load"):
            dashboard.load()

    # ------------------------------------------------------------------
    # Queue polling (runs in main thread every QUEUE_POLL_MS)
    # ------------------------------------------------------------------

    def _check_queue(self) -> None:
        try:
            while True:
                msg_type, payload = self._queue.get_nowait()
                self._handle_queue_msg(msg_type, payload)
        except queue.Empty:
            pass
        finally:
            self.after(self.QUEUE_POLL_MS, self._check_queue)

    def _handle_queue_msg(self, msg_type: str, payload: object) -> None:
        status_bar = self._window.status_bar
        if msg_type == _MSG_PROGRESS:
            data = payload  # type: ignore[assignment]
            status_bar.update_progress(
                step=data.get("step", 0),
                total=data.get("total", 0),
                label=data.get("label", ""),
            )
        elif msg_type == _MSG_COMPLETE:
            import datetime
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            status_bar.show_ready(ts)
            dashboard = self._pages.get("dashboard")
            if dashboard and hasattr(dashboard, "load"):
                dashboard.load()
            # Also refresh stock detail page if a symbol is currently loaded
            stock_detail = self._pages.get("stock_detail")
            if stock_detail and hasattr(stock_detail, "load") and getattr(stock_detail, "_current_symbol", ""):
                stock_detail.load(stock_detail._current_symbol)
            # Also refresh watchlist page (prices may have been updated)
            watchlist = self._pages.get("watchlist")
            if watchlist and hasattr(watchlist, "load"):
                watchlist.load()
        elif msg_type == _MSG_ERROR:
            status_bar.show_error(str(payload))

    # ------------------------------------------------------------------
    # Background update
    # ------------------------------------------------------------------

    def _start_update(self) -> None:
        """Trigger background update via UpdateService (if wired)."""
        update_svc = getattr(self, "_update_service", None)
        if update_svc is not None:
            update_svc.start_background_update()

    def wire_update_service(self, update_service) -> None:
        """Called after DI setup to attach UpdateService and trigger initial check."""
        self._update_service = update_service
        if update_service.check_needs_update():
            self._start_update()
