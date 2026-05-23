# Tasks: Midas — 台股盤後投研桌面應用 MVP

**Branch**: `001-midas-mvp` | **Generated**: 2026-05-19
**Input**: [spec.md](spec.md) | [plan.md](plan.md) | [data-model.md](data-model.md) | [contracts/service-interfaces.md](contracts/service-interfaces.md)

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: 可平行執行（不同檔案、無未完成的依賴）
- **[US1–US5]**: 對應使用者故事（US-01 盤後看板 / US-02 個股事件 / US-03 財務快覽 / US-04 追蹤清單 / US-05 自動更新）
- 每個任務工作量估計：0.5–2 天

---

## Phase A: 專案初始化 (Project Setup)

**目的**: 建立可運行的 Python 專案骨架，所有後續 phase 都依賴此基礎
**預估**: 0.5 天

- [x] T001 初始化 uv 專案：執行 `uv init` 並設定 `pyproject.toml`（Python 3.12、所有依賴：customtkinter, finmindapi, requests, beautifulsoup4, google-generativeai, platformdirs, pytest, pytest-mock）
- [x] T002 [P] 建立完整目錄結構：`src/midas/{ui,viewmodels,services,agents,repositories,models,integrations,tasks}/`、`tests/{unit,integration}/`、`scripts/`（依 plan.md Project Structure）
- [x] T003 [P] 建立 `.env.example`（含 `FINMIND_TOKEN=`, `GEMINI_API_KEY=`, `MIDAS_DB_PATH=`）與 `.gitignore`（含 `.env`, `*.db`, `dist/`, `build/`）
- [x] T004 [P] 設定開發工具：`ruff`（linting + formatting）、`pytest.ini`（`testpaths=tests`、`markers = integration`）於 `pyproject.toml`
- [x] T005 建立 `src/midas/config.py`：`AppConfig` dataclass，讀取 `APPDATA/Midas` 路徑（用 `platformdirs`）、載入 `.env` 環境變數（`FINMIND_TOKEN`, `GEMINI_API_KEY`）

**Checkpoint A**: `uv sync` 成功、`pytest` 執行零 test 無報錯、`python -c "from midas.config import AppConfig; print(AppConfig())"` 可執行

---

## Phase B: 桌面骨架 (Desktop Shell)

**目的**: 建立可見的 GUI 應用框架，驗證 CTk 頁面切換機制，不含任何業務資料
**依賴**: Phase A 完成
**預估**: 1 天

- [x] T006 建立 `src/midas/ui/theme.py`：定義顏色常數（深色/亮色 palette）、CTk `set_appearance_mode` 初始化邏輯
- [x] T007 建立 `src/midas/ui/app_window.py`：`AppWindow(ctk.CTkFrame)`，包含 1280×800 視窗、左側 `SidebarNav`（180px）佔位框、右側內容區 `ContentArea`（CTkFrame 容器）、底部 `StatusBar`（28px）
- [x] T008 [P] 建立 `src/midas/ui/components/sidebar_nav.py`：`SidebarNav(ctk.CTkFrame)`，含首頁/自選股/資源監控/設定四個導航按鈕，點擊時呼叫 callback `on_navigate(page_name: str)`
- [x] T009 [P] 建立 `src/midas/ui/components/status_bar.py`：`StatusBar(ctk.CTkFrame)`，含更新時間標籤、進度文字標籤、重試按鈕（預設隱藏）；提供 `update_progress(step, total, label)`、`show_error(msg)`、`show_ready(timestamp)` 方法
- [x] T010 建立 5 個頁面佔位 Frame（僅標題文字）：`src/midas/ui/pages/{dashboard_page,stock_detail_page,watchlist_page,settings_page,resource_monitor_page}.py`；每個 page 為 `ctk.CTkFrame` 子類別
- [x] T011 建立 `src/midas/app.py`：`App(ctk.CTk)`，在 `__init__` 中初始化所有 Page Frame、以 `tkraise()` 實作頁面切換、連接 `SidebarNav` callback；啟動 `self.after(500, self._check_queue)`（queue 輪詢佔位）
- [x] T012 建立 `main.py`：呼叫 `App().mainloop()`；設定 `ctk.set_appearance_mode("dark")` 預設深色
- [x] T013 驗證主題切換機制：在 `app.py` 加入暫時性呼叫確認 `ctk.set_appearance_mode("dark")` / `ctk.set_appearance_mode("light")` 可正常切換（骨架期驗證）；Phase B 不在 SettingsPage 加入切換按鈕，完整設定頁面主題切換由 T055 負責

**Checkpoint B**: `python main.py` 啟動後顯示主視窗，5 個導航按鈕可切換頁面，深色/亮色可切換，冷啟動 < 3 秒

---

## Phase C: 本機資料層 (Data Layer)

**目的**: 建立完整的 SQLite schema、Dataclasses、Repositories，為所有資料操作提供持久化基礎
**依賴**: Phase A 完成（Phase B 可平行進行）
**預估**: 1.5 天

### C-1: Models & Schema

- [x] T014 [P] 建立所有 Python dataclasses（5 個檔案）：
  - `src/midas/models/tracked_stock.py`：`TrackedStock` dataclass
  - `src/midas/models/market_event.py`：`MarketEvent` dataclass + `EventType` enum + `Sentiment` enum
  - `src/midas/models/financial_metric.py`：`FinancialMetric` dataclass + `MetricType` enum + `Direction` enum
  - `src/midas/models/market_overview.py`：`MarketOverview` dataclass
  - `src/midas/models/update_job.py`：`UpdateJob` dataclass（`JobStatus` enum：running/success/failed/partial）
- [x] T014a [P] 建立 `src/midas/exceptions.py`：定義所有自訂例外類別：`MidasError`（基底）、`DataFetchError(source: str, reason: str, retryable: bool)`、`LLMQuotaExceededError`、`CacheExpiredError`、`WatchlistLimitError`；T025、T036、T039、T043、T057 均依賴此模組
- [x] T015 建立 `src/midas/repositories/database.py`：`DatabaseManager`，負責確認 `%APPDATA%\Midas\` 目錄存在、建立 SQLite 連線、執行 `PRAGMA user_version = 1`、建立所有 5 張資料表（`tracked_stocks, market_events, financial_metrics, market_overviews, update_jobs`）及 `app_settings` KV 表、建立索引、插入預設 `app_settings`
- [x] T016 [P] 建立所有 Repository ABCs：`src/midas/repositories/interfaces.py`（含 `ITrackedStockRepository`, `IMarketEventRepository`, `IFinancialMetricRepository`, `IMarketOverviewRepository`, `IUpdateJobRepository`，依 `contracts/service-interfaces.md`）

### C-2: Repository Implementations

- [x] T017 [P] 建立 `src/midas/repositories/tracked_stock_repo.py`：實作 `ITrackedStockRepository`（`add, remove, get_all, get_by_symbol, update_memo, count, search_by_symbol_or_name(query: str) -> list[TrackedStock]`）；新增股票使用 `INSERT OR IGNORE`（防止重複新增覆蓋 `added_at`）；更新備忘/排序時使用 `UPDATE ... WHERE symbol=?`（不觸碰 `added_at`）
- [x] T018 [P] 建立 `src/midas/repositories/market_event_repo.py`：實作 `IMarketEventRepository`（`upsert_many, get_by_symbol_date, get_today_events_for_symbols`）；`upsert_many` 使用 `INSERT ... ON CONFLICT(symbol, event_date, source_url) DO UPDATE`（去重且允許覆寫 `occurred_at/title/source_name/fetched_at`）
- [x] T019 [P] 建立 `src/midas/repositories/financial_metric_repo.py`：實作 `IFinancialMetricRepository`（`upsert_many, get_by_symbol, is_cache_valid`）；`is_cache_valid` 判斷最後 `fetched_at` 是否在 7 天內
- [x] T020 [P] 建立 `src/midas/repositories/market_overview_repo.py`：實作 `IMarketOverviewRepository`（`upsert, get_by_date, get_latest`）
- [x] T021 [P] 建立 `src/midas/repositories/update_job_repo.py`：實作 `IUpdateJobRepository`（`create, update_progress, complete, fail, get_latest, get_history`）

### C-3: Unit Tests (Data Layer)

- [x] T022 [P] 建立 `tests/unit/test_cache_strategy.py`：測試 `FinancialMetricRepo.is_cache_valid()` 在不同 `fetched_at` 情境（7 天內 / 超過 7 天 / NULL）；使用 in-memory SQLite（`:memory:`）
- [x] T023 [P] 建立 `tests/integration/test_sqlite_repos.py`（標記 `@pytest.mark.integration`）：對真實 in-memory SQLite 測試所有 Repo 的 CRUD + upsert 衝突更新 + constraint 驗證

**Checkpoint C**: `pytest tests/unit/test_cache_strategy.py` 全綠；`python -c "from midas.repositories.database import DatabaseManager; DatabaseManager().init()"` 建立 DB 不報錯；所有 5 張表存在

---

## Phase D: 市場資料整合 (FinMind Integration)

**目的**: 封裝 FinMind API，含配額控管、快取檢查、重試邏輯；為 MarketAgent + FinancialAgent 提供資料基礎
**依賴**: Phase C 完成
**對應**: US-01（大盤概況）、US-03（財務資料）、US-05（背景更新）
**預估**: 1.5 天

- [x] T024 建立 `src/midas/integrations/finmind_client.py`：`FinMindClient` 類別，含：
  - Token 管理（從 `AppConfig` 讀取 `FINMIND_TOKEN`）
  - 請求速率控制（每小時 600 次上限；in-memory 累計計數器追蹤本次更新回合的請求數；若累計達 800 次，拋出 `DataFetchError(retryable=False)` 中止更新）
  - HTTP 429 處理：等待 60 秒後重試，最多 3 次
  - HTTP 5xx：指數退避重試（base=2, max=3）
  - 所有請求 `timeout=15`
  - 方法：`get_market_overview(date: str) -> dict`、`get_institutional_investors(date: str) -> dict`、`get_sector_rankings(date: str) -> list`、`get_financial_statements(symbol: str, start_date: str) -> dict`、`get_stock_info(symbol: str) -> dict`
- [x] T025 建立 `tests/unit/test_finmind_client_quota.py`：測試當日請求數超過 800 時拋出 `DataFetchError`、測試 429 重試邏輯（mock requests）；**不呼叫真實 API**
- [x] T026 建立 `tests/integration/test_finmind_client.py`（`@pytest.mark.integration`）：對真實 FinMind API 的端對端測試，需設定 `FINMIND_TOKEN`

**Checkpoint D**: `pytest tests/unit/test_finmind_client_quota.py` 全綠；手動執行 `FinMindClient().get_stock_info("2330")` 回傳台積電資料

---

## Phase E: 事件資料整合 (FinMind 新聞整合)

**目的**: 封裝 FinMind TaiwanStockNews API，含事件分類、正規化、去重寫入；為 AnnouncementAgent 提供資料基礎
**依賴**: Phase C 完成（Phase D 可平行進行）
**對應**: US-01（首頁事件）、US-02（個股事件）
**預估**: 1.5 天

- [x] T027a [P] 建立 `src/midas/agents/interfaces.py`：所有 Agent ABCs（`IMarketAgent`、`IAnnouncementAgent`、`IFinancialAgent`、`ISummarizationAgent`、`IOrchestrator`），含方法簽章及 docstring，依 `contracts/service-interfaces.md`；`IMarketAgent` 包含 `fetch_overview(date)` 與 `get_stock_info(symbol) -> dict`（供 WatchlistService 注入使用）
- [x] T027 建立 `src/midas/agents/announcement_agent.py` 中 FinMind 新聞抓取逻輯：
  - 呼叫 `FinMindClient.get_stock_news(symbol, date)`，使用 TaiwanStockNews REST API
  - 回傳欄位：`title`, `description`, `link`, `source`, `date`, `stock_id`
  - 請求成功後記錄 `_request_count += 1`
  - 失敗處理：記錄 warning log，回傳空列表（不中斷整體更新）
  - 建議將此項定義為建立 `src/midas/integrations/finmind_client.py` 中 `get_stock_news` 方法的次項
- [x] T028 建立 `src/midas/agents/announcement_agent.py`：`AnnouncementAgent`，實作 `IAnnouncementAgent`：
  - `_classify_event(title: str, page_code: str) -> EventType`：根據標題關鍵字判斷類型（財報/法說/重訊/一般）
  - `_normalize_news(raw: dict, symbol: str) -> MarketEvent`：原始 FinMind 新聞 dict → MarketEvent dataclass（時間使用 `occurred_at`）
  - `fetch_announcements(symbol: str, date: str) -> list[MarketEvent]`：呼叫 `FinMindClient.get_stock_news()` → 分類 → 正規化
- [x] T029 建立 `tests/unit/test_event_classifier.py`：測試 `_classify_event()` 的各種標題輸入（含邊界案例：空白標題、含財報關鍵字的法說標題）；mock FinMindClient 回傳假資料
- [x] T030 [P] `tests/fixtures/sample_mops_announcement.html`：舊版 MOPS HTML 假資料（已不使用，保留供參考）

**Checkpoint E**: `pytest tests/unit/test_event_classifier.py` 全綠；`AnnouncementAgent().fetch_announcements("2330", "2026-05-19")` 可執行（mock FinMindClient）

---

## Phase F: 分析與摘要 (Analysis & Summarization)

**目的**: 實作財務五大指標計算邏輯、FinancialAgent；Gemini 摘要管線含配額控制；所有計算在 Python 層完成，LLM 不做數值運算
**依賴**: Phase D + Phase E 完成
**對應**: US-02（事件摘要）、US-03（財務指標）
**預估**: 2 天

### F-1: 財務指標計算

- [x] T031 建立 `src/midas/agents/financial_agent.py`：`FinancialAgent`，實作 `IFinancialAgent`：
  - `_calculate_metrics(raw_data: dict, symbol: str) -> list[FinancialMetric]`：
    - EPS：直接取值
    - 毛利率：`GrossProfit / (GrossProfit + COGS) * 100`
    - ROE：`IncomeAfterTaxes / Equity * 100`
    - 負債比：`TotalLiabilities / TotalAssets * 100`
    - FCF：`OperatingCF - CapEx`（百萬元）
    - 方向計算：`change_pct = (cur - prev) / abs(prev) * 100`；`> +5` = improving, `< -5` = declining
    - `is_unreported=True` 若該季無資料
  - `fetch_and_calculate(symbol: str) -> list[FinancialMetric]`：呼叫 FinMindClient（`start_date` = 今日往前推 1095 天，即約 3 年 ≈ 12 季）→ 計算 → 回傳最近 12 季
- [x] T032 建立 `tests/unit/test_financial_calculator.py`：測試 5 大指標計算 + ±5% 方向判定邏輯（含邊界：`change_pct = +5.0`、`prev = 0`、`is_unreported` 情境）；使用 `fixtures/sample_finmind_financial.json`
- [x] T033 [P] 建立 `tests/fixtures/sample_finmind_financial.json`：仿 FinMind `TaiwanStockFinancialStatements` API 回應格式（12 季資料，含 NULL 季度）
- [x] T033a [P] 建立 `tests/fixtures/sample_finmind_price.json`：仿 FinMind 大盤日線資料 API 回應格式（加權指數、成交量、三大法人資料），供 MarketAgent.fetch_overview 測試使用

### F-2: LLM 摘要管線

- [x] T034 建立 `src/midas/integrations/gemini_client.py`：`GeminiClient` 類別，含：
  - `MODEL = "gemini-3.5-flash"`
  - 每次呼叫前：讀取 `app_settings.llm_daily_calls`；若 >= 50 且 `llm_daily_date` = 今日 → 拋出 `LLMQuotaExceededError`（實作 FR-032 每日 50 次配額上限）
  - 每次呼叫後：更新 `llm_daily_calls + 1`、`llm_daily_date`
  - `generate(system_prompt: str, user_text: str) -> str`：呼叫 Gemini API，回傳 JSON 字串
  - `SYSTEM_PROMPT` 常數：長期投資框架分析觀點，輸出【新聞摘要】+【分析解讀】①②③ 結構化格式，禁止買賣建議、禁止數値計算
- [x] T035 建立 `src/midas/agents/summarization_agent.py`：`SummarizationAgent`，實作 `ISummarizationAgent`：
  - `summarize_events(symbol: str, events: list[MarketEvent]) -> list[MarketEvent]`：
    - 批次打包同公司所有事件為單次 LLM 呼叫
    - 解析 JSON 回應 `{"events": [{"id": ..., "summary": ..., "sentiment": ...}]}`
    - 驗證：摘要 80–800 字（含【新聞摘要】+【分析解讀】結構化格式）、sentiment 限三選一
    - LLM 失敗時：不修改 event（`ai_summary = None`），不中斷整體更新
- [x] T036 建立 `tests/unit/test_summarization_quota.py`：測試每日 50 次配額控制（第 51 次拋出 `LLMQuotaExceededError`）、測試日期重置邏輯；mock GeminiClient
- [x] T037 [P] 建立 `tests/fixtures/sample_gemini_response.json`：含 3 筆事件摘要的完整 JSON 回應樣本

**Checkpoint F**: `pytest tests/unit/test_financial_calculator.py tests/unit/test_summarization_quota.py` 全綠；計算邏輯通過所有邊界條件

---

## Phase G: 核心頁面實作 (Core Pages)

**目的**: 實作 5 個頁面的完整 UI + ViewModel + Service，可從 SQLite 讀取資料顯示（不依賴真實 API）
**依賴**: Phase B（骨架）+ Phase C（資料層）完成；Phase D/E/F 資料可用 fixtures 替代
**預估**: 3 天（G-1 和 G-2 可平行）

### G-1: Service Layer (先備)

- [x] T038 建立 `src/midas/services/interfaces.py`：所有 Service ABCs（`IWatchlistService`, `IEventService`, `IFinancialService`, `IMarketService`, `IUpdateService`，依 `contracts/service-interfaces.md`）
- [x] T039 [P] 建立 `src/midas/services/watchlist_service.py`：`WatchlistService`，實作 `IWatchlistService`，注入 `ITrackedStockRepository` + `IMarketAgent`：
  - `add`：驗證 4–6 碼純數字 → 呼叫 `IMarketAgent.get_stock_info(symbol)` 取公司名 → TrackedStockRepo.add()；若已達 30 檔拋出 `WatchlistLimitError`（不直接依賴 FinMindClient）
  - `remove`：TrackedStockRepo.remove()
  - `update_memo`：驗證 ≤ 500 字 → TrackedStockRepo.update_memo()
  - `search`：TrackedStockRepo.search_by_symbol_or_name()
- [x] T040 [P] 建立 `src/midas/services/event_service.py`：`EventService`，實作 `IEventService`：`get_today_events()` 回傳已按 `(event_type_priority ASC, occurred_at DESC)` 排序的列表（職責說明：EventService 負責單一追蹤股的事件內部排序規則 FR-027；跨股票分組由 DashboardViewModel T044 負責）
- [x] T041 [P] 建立 `src/midas/services/financial_service.py`：`FinancialService`，實作 `IFinancialService`：`get_metrics()` 回傳 `dict[MetricType, list[FinancialMetric]]`（最舊到最新）
- [x] T042 [P] 建立 `src/midas/services/market_service.py`：`MarketService`，實作 `IMarketService`：`get_today_overview()` 回傳最新 MarketOverview 或 None
- [x] T043 建立 `tests/unit/test_watchlist_service.py`：測試 CRUD、30 檔上限（第 31 筆拋 WatchlistLimitError）、備忘 501 字拋 ValueError、搜尋篩選；全 mock ITrackedStockRepository + mock IMarketAgent（`get_stock_info` 回傳假資料）

### G-2: ViewModels

- [x] T044 [P] 建立 `src/midas/viewmodels/dashboard_vm.py`：`DashboardViewModel`，注入 `IMarketService` + `IEventService` + `IWatchlistService`：
  - `get_today_events()` → 有事件的追蹤股在上，無事件的淡色在下（分組邏輯在 ViewModel；每股事件清單直接使用 EventService 回傳的已排序列表，ViewModel 不重複排序）
  - `get_market_overview()` → MarketOverview or None
  - `get_last_update_timestamp()` → str (YYYY-MM-DD HH:MM 更新)
- [x] T045 [P] 建立 `src/midas/viewmodels/stock_detail_vm.py`：`StockDetailViewModel`，注入 `IEventService` + `IFinancialService`：
  - `load_events(symbol, date)` → `list[MarketEvent]`（依 priority 排序）
  - `load_metrics(symbol)` → `dict[str, list[FinancialMetric]]`（12 季，最舊到最新）
- [x] T046 [P] 建立 `src/midas/viewmodels/watchlist_vm.py`：`WatchlistViewModel`，注入 `IWatchlistService`：包裝 add/remove/update_memo/search 呼叫

### G-3: UI Components

- [x] T047 [P] 建立 `src/midas/ui/components/market_overview_card.py`：`MarketOverviewCard(ctk.CTkFrame)`，顯示加權指數、漲跌幅、成交量 vs 五日均量、前五大漲跌產業、三大法人；接受 `MarketOverview | None`（None 時顯示「暫無資料」）
- [x] T048 [P] 建立 `src/midas/ui/components/event_list_item.py`：`EventListItem(ctk.CTkFrame)`，顯示公司名、股票代號、事件類型標籤（色彩區分）、發生時間、AI 摘要一行（≤50 字）；點擊觸發 `on_click(symbol)` callback
- [x] T049 [P] 建立 `src/midas/ui/components/stock_event_card.py`：`StockEventCard(ctk.CTkFrame)`，顯示事件標題、分類標籤、AI 摘要（結構化格式【新聞摘要】+【分析解讀】，以 CTkTextbox 顯示）、語意傾向標籤（三色）、來源名稱 + occurred_at（報導發布時間）、「查看原文」按鈕（`webbrowser.open(url)`）、免責聲明文字（固定顯示）、「🔄 重新分析」按鈕（AI 完成後顯示）、分析期間 CTkProgressBar 動畫
- [x] T050 [P] 建立 `src/midas/ui/components/financial_metric_row.py`：`FinancialMetricRow(ctk.CTkFrame)`，顯示指標名稱、12 季數值表格、方向標示（↑↓→ 含顏色）、來源 + 更新時間；`is_unreported=True` 時顯示「尚未揭露」

### G-4: Page Implementations [US-01 ~ US-05]

- [x] T051 [US1] [US4] 完整實作 `src/midas/ui/pages/dashboard_page.py`：注入 `DashboardViewModel`；`load()` 方法清空並重建 `MarketOverviewCard` + `EventListItem` 清單；事件清單依 ViewModel 回傳順序渲染；無事件時顯示「今日無重要事件」；點選 EventListItem → `controller.show_frame(StockDetailPage, symbol=symbol)`
- [x] T052 [US2] [US3] 完整實作 `src/midas/ui/pages/stock_detail_page.py`：含「事件」+ 「財務」兩個 CTkTabview；`load(symbol)` 呼叫 ViewModel；事件分頁渲染 `StockEventCard` 列表；財務分頁渲染 `FinancialMetricRow` 列表；無事件時顯示「今日無公告或事件」
- [x] T053 [US4] 完整實作 `src/midas/ui/pages/watchlist_page.py`：追蹤股清單 + 新增輸入框（4–6 碼驗證）+ 刪除按鈕（含確認對話框）+ 備忘編輯框；即時搜尋篩選；達 30 檔顯示「已達上限（30 檔）」
- [x] T054 [US5] 建立 `src/midas/ui/pages/resource_monitor_page.py`：`ResourceMonitorPage(ctk.CTkFrame)`，顯示資源監控指標：
  - Gemini 區塊：Key 狀態、前往 AI Studio 使用量連結
  - FinMind 區塊：Token 狀態、每小時 API 用量進度條
  - 本機快取區塊：最後更新、資料筆數、DB 大小
  - 【重新整理】按鈕
- [x] T055 完整實作 `src/midas/ui/pages/settings_page.py`：FinMind Token 輸入欄（儲存至 `app_settings`）、Gemini API Key 輸入欄（儲存至 `app_settings`）、深色/亮色切換、「清除快取」按鈕（清空 `market_events` + `financial_metrics`）

**Checkpoint G**: 以 `scripts/load_fixtures.py` 載入假資料後，`python main.py` 可在首頁看到事件清單、點進個股詳情看到事件 + 財務分頁、在追蹤清單頁新增/刪除股票

---

## Phase H: 背景更新管線 (Background Update Pipeline)

**目的**: 實作完整的 Orchestrator + BackgroundWorker + queue 通訊，讓應用啟動時可自動觸發盤後更新而不阻塞 UI
**依賴**: Phase D + E + F（Agents 完整）+ Phase G Service Layer 完成
**對應**: US-05
**預估**: 2 天

- [x] T056 建立 `src/midas/tasks/background_worker.py`：`BackgroundWorker`，管理 `threading.Thread(daemon=True)` + `queue.Queue`：
  - `start(task_fn: Callable, *args)` → 啟動背景執行緒執行 `task_fn`
  - `is_running() -> bool`
  - worker thread 捕獲未預期例外時 `put(("update_error", str(e)))`；正常完成由 Orchestrator Step 5 的 `put(("update_complete", job))` 負責（BackgroundWorker 不發送 `("done", None)` 訊號）
- [x] T057 建立 `src/midas/agents/orchestrator.py`：`Orchestrator`，實作 5 步驟更新管線（依 plan.md Data Flow）：
  - Step 1：`MarketAgent.fetch_overview(today)` → `MarketOverviewRepo.upsert()`
  - Step 2：for each symbol → `AnnouncementAgent.fetch_announcements()` → `MarketEventRepo.upsert_many()`
  - Step 3：for each symbol（快取過期）→ `FinancialAgent.fetch_and_calculate()` → `FinancialMetricRepo.upsert_many()`
  - Step 4：for each symbol with events → `SummarizationAgent.summarize_events()` → `MarketEventRepo.upsert_many()`
  - Step 5：`UpdateJobRepo.complete()` + `queue.put(("update_complete", update_job))`
  - 每步驟完成：`queue.put(("progress", {"step": n, "total": N, "label": label}))`
  - 任意步驟 exception：`UpdateJobRepo.fail(error_msg)` + `queue.put(("update_error", msg))`
- [x] T058 建立 `src/midas/agents/market_agent.py`：`MarketAgent`，實作 `IMarketAgent`：
  - `fetch_overview(date: str) -> MarketOverview`：呼叫 FinMindClient 取大盤指數 + 成交量 + 三大法人 + 類股排行，組合為 `MarketOverview` dataclass
  - `get_stock_info(symbol: str) -> dict`：呼叫 `FinMindClient.get_stock_info(symbol)` 取公司名稱與產業，回傳 `{'symbol': ..., 'company_name': ..., 'industry': ...}`（供 WatchlistService 使用）
- [x] T059 建立 `src/midas/services/update_service.py`：`UpdateService`，實作 `IUpdateService`：
  - `check_needs_update() -> bool`：讀 `app_settings.last_update_date`；若今日 >= 15:00 且 `last_update_date != today` → True；非交易日（週六/週日或假日，以 `HolidayCalendar.is_trading_day(today)` 判斷，見 T059a）→ 直接回傳 False
  - `start_background_update(on_progress, on_complete, on_error)`：呼叫 `BackgroundWorker.start(orchestrator.run, symbols)`，callback 透過 queue 傳遞
- [x] T059a 建立 `src/midas/utils/holiday_calendar.py`：`HolidayCalendar`，提供 `is_trading_day(date: str) -> bool`：
  - 啟動時以 `requests.get` 從 TWSE OpenAPI（`https://opendata.twse.com.tw/v1/holidaySchedule/holidaySchedule`）取得當年假日清單，存入 `_holiday_set: set[str]`（格式 YYYY-MM-DD）；API 失敗時 `_holiday_set = set()`（保守策略：清單不可得時不阻擋更新）
  - `is_trading_day()` 回傳 False 情況：週六、週日、或日期在 `_holiday_set` 中
- [x] T060 在 `src/midas/app.py` 完整實作 `_check_queue()` 輪詢：處理 `("progress", ...)` → `StatusBar.update_progress()`；`("update_complete", job)` → `DashboardPage.load()` + `StatusBar.show_ready()`；`("update_error", msg)` → `StatusBar.show_error()`
- [x] T061 在 `App.__init__()` 末尾：
  - 將 `StatusBar` 的 retry 按鈕 `command` 設為 `lambda: self._start_update()`（`_start_update` 為呼叫 `UpdateService.start_background_update(...)` 的內部方法，初次啟動與重試共用相同 callbacks）
  - 呼叫 `UpdateService.check_needs_update()`；若 True 則 `self._start_update()`
- [x] T062 建立 `tests/unit/test_update_orchestrator.py`：測試 Orchestrator 5 步驟流程控制（全 Mock Agents + Repos）；測試 Step 2/3/4 失敗時 UpdateJob.status = 'partial'/'failed'；測試 queue 訊息格式正確

**Checkpoint H**: 啟動應用、等待 15:00 後（或修改 `last_update_date` 為昨天觸發更新）→ StatusBar 顯示進度 `正在更新… 1/5`、更新完成後 `首頁` 自動刷新、主介面在更新期間可正常切換頁面

---

## Phase I: 整合驗收 (Integration)

**目的**: 端對端驗收所有 User Story、錯誤情境與效能
**依賴**: Phase A–H 全部完成
**預估**: 1 天

### I-1: 整合測試與驗收

- [x] T063 [P] 建立 `scripts/load_fixtures.py`：插入 3 筆 `tracked_stocks`、每股 3–5 筆 `market_events`（含各 EventType）、每股 12 季 `financial_metrics`、1 筆 `market_overviews`；供本機手動驗收使用
- [x] T064 [P] 建立 `scripts/reset_db.py`：刪除 `%APPDATA%\Midas\midas.db` 並重建空白 DB
- [ ] T065 [US1] 手動驗收 US-01 接受情境全部 5 項（依 spec.md Acceptance Scenarios）；記錄驗收結果於 `specs/001-midas-mvp/checklists/acceptance-us01.md`
- [ ] T066 [US2] 手動驗收 US-02 接受情境全部 5 項；記錄於 `specs/001-midas-mvp/checklists/acceptance-us02.md`
- [ ] T067 [US3] 手動驗收 US-03 接受情境全部 5 項；記錄於 `specs/001-midas-mvp/checklists/acceptance-us03.md`
- [ ] T068 [US4] 手動驗收 US-04 接受情境全部 5 項；記錄於 `specs/001-midas-mvp/checklists/acceptance-us04.md`
- [ ] T069 [US5] 手動驗收 US-05 接受情境全部 5 項；記錄於 `specs/001-midas-mvp/checklists/acceptance-us05.md`

### I-2: 錯誤情境驗收

- [ ] T070 [P] 驗收 Edge Cases（依 spec.md）：
  - 追蹤清單為空 → 首頁顯示「尚未新增追蹤股」引導
  - AI 摘要生成失敗 → 顯示「AI 摘要暫不可用，請查看原文連結」
  - FinMind 回傳錯誤 → 財務分頁顯示「資料暫時無法取得，上次更新：[timestamp]」
  - 更新中關閉應用 → 下次啟動正常重啟更新
  - 非交易日（週末/假日）開啟應用 → 顯示最後交易日資料並標注日期（格式：「上次交易日：YYYY-MM-DD」）；`UpdateService.check_needs_update()` 正確回傳 False

### I-3: 效能驗收

- [ ] T071 [P] 效能驗收（依 spec.md Success Criteria）：
  - SC-001：冷啟動 < 15 秒可見今日事件清單（快取情況）
  - SC-004：首頁切換響應 < 200ms（用 stopwatch 量測）
  - plan.md NFR：冷啟動至首頁顯示 < 3 秒（空 watchlist）
  - plan.md NFR：30 檔盤後完整更新 < 10 分鐘（15:00 後實測）

### I-4: 打包（Deferred）

- [ ] T072 [Deferred] 打包規格維護：未納入目前 MVP 範圍，待後續版本再加入。
- [ ] T073 [Deferred] 可執行檔驗收：未納入目前 MVP 範圍，待後續版本再加入。

**Checkpoint I**: 所有 US-01 ~ US-05 驗收清單全綠；`pytest tests/unit/` 全綠（0 failures）

---

## Dependencies & Execution Order

### Phase 依賴圖

```
Phase A（專案初始化）
    ├─→ Phase B（GUI 骨架）
    └─→ Phase C（資料層）
              ├─→ Phase D（FinMind）
              ├─→ Phase E（FinMind 新聞）
              │         └─┐
              │    Phase F（計算 + 摘要）← Phase D + E
              │         └─┐
              Phase B + C + F ─→ Phase G（核心頁面）
                                       └─→ Phase H（背景更新）← D+E+F+G
                                                   └─→ Phase I（驗收）
```

### User Story 依賴

| User Story | 必要 Phase | 可並行開始 |
|-----------|-----------|---------|
| US-01 盤後摘要看板 | A + B + C + E + F + G（DashboardPage） | 需要 Phase G-4 T051 |
| US-02 個股事件詳情 | A + B + C + E + F + G（StockDetailPage 事件 Tab） | 與 US-01 可並行（G-3 元件各自獨立） |
| US-03 財務健康快覽 | A + B + C + D + F + G（StockDetailPage 財務 Tab） | 與 US-01/02 可並行 |
| US-04 追蹤清單 | A + B + C + G（WatchlistPage） | 最獨立，可最早完成 |
| US-05 自動更新 | 全部 A–G + Phase H | 最後完成 |

### 並行機會

**Phase A 完成後可同時進行**：
- Phase B（GUI 骨架）
- Phase C（資料層：T014–T021 大部分可並行）

**Phase C 完成後可同時進行**：
- Phase D（FinMind）
- Phase E（FinMind 新聞整合）

**Phase D + E 完成後**：
- Phase F（計算 + 摘要）

**Phase B + C 完成後（Phase F 可先用 fixtures）**：
- Phase G（G-1 Service 和 G-2 ViewModel 和 G-3 Components 可三路並行）

---

## 並行執行範例：Phase C（資料層）

```
Day 1 上午:
├─ [你]  T014 建立所有 Models / Dataclasses（所有下游均依賴）
└─ [你]  T015 建立 DatabaseManager + Schema

Day 1 下午（T014+T015 完成後並行）:
├─ [你/A]  T016 Repository ABCs
├─ [你/B]  T017 TrackedStockRepo
├─ [你/C]  T018 MarketEventRepo

Day 2 上午:
├─ [繼續]  T019 FinancialMetricRepo
├─ [繼續]  T020 MarketOverviewRepo
├─ [繼續]  T021 UpdateJobRepo

Day 2 下午:
└─ T022 + T023 測試
```

---

## MVP 建議執行範圍（最小可驗收）

**MVP 核心**（優先完成 US-04 → US-01 垂直切片）：

1. **Phase A**（必要）
2. **Phase B**（必要，骨架）
3. **Phase C**（必要，持久化）
4. **Phase E**（FinMind 新聞整合）+ **Phase G-1/G-2/G-3/G-4 T053**（WatchlistPage）→ **US-04 完成**
5. **Phase G-4 T051**（DashboardPage，搭配 fixtures） → **US-01 基本驗收可過**
6. **Phase G-4 T052**（StockDetailPage 事件 Tab） → **US-02 完成**
7. **Phase F-1**（財務計算）+ **Phase D**（FinMind）+ **Phase G-4 T052 財務 Tab** → **US-03 完成**
8. **Phase H**（背景更新）→ **US-05 完成**
9. **Phase I**（驗收 + 打包）

**建議 MVP 里程碑**：Phase A–C + US-04（WatchlistPage）+ US-01（DashboardPage with fixtures）= 3–4 天內可看到第一個有資料的可運行應用

---

## 任務統計

| Phase | 任務數 | 預估天數 | 對應 User Story |
|-------|--------|---------|----------------|
| A 初始化 | T001–T005 (5) | 0.5 | — |
| B 骨架 | T006–T013 (8) | 1.0 | — |
| C 資料層 | T014–T023 + T014a (11) | 1.5 | — |
| D FinMind | T024–T026 (3) | 1.5 | US-01, US-03, US-05 |
| E FinMind 新聞 | T027a–T030 (5) | 1.5 | US-01, US-02 |
| F 分析摘要 | T031–T037 + T033a (8) | 2.0 | US-02, US-03 |
| G 核心頁面 | T038–T055 (18) | 3.0 | US-01~US-04 |
| H 背景更新 | T056–T062 (7) | 2.0 | US-05 |
| I 驗收打包 | T063–T073 (11) | 1.0 | 全部 |
| **合計** | **76 個任務** | **~14 天** | |

**並行機會識別**：共 **27 個任務**標有 `[P]`，Phase C 最多並行點（8 個 `[P]` 任務）
