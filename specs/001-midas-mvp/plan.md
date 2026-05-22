# Implementation Plan: Midas — 台股盤後投研桌面應用 MVP

**Branch**: `001-midas-mvp` | **Date**: 2026-05-19 → MVP Complete 2026-05-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-midas-mvp/spec.md`

## Summary

Midas 是以 Multi-Agent 架構驅動的台股盤後投研桌面應用（Windows 10/11）。MVP 以 CustomTkinter 為 GUI 框架，FinMind（免費方案）為全面資料來源（股價、財務、新聞公告、交易日、三大法人），Gemini （`gemini-3.5-flash`）為摘要 LLM，SQLite 為本機儲存。應用啟動時自動偵測盤後狀態，以背景執行緒觸發 code-based 多 Agent 更新管線，主畫面不阻塞。提供盤後摘要看板、個股事件詳情、財務健康快覽、追蹤清單管理六大 MVP 功能。

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: customtkinter, FinMind（finmindapi），requests, google-generativeai, platformdirs, pytest, pytest-mock, PyInstaller

**Storage**: SQLite — `%APPDATA%\Midas\midas.db`（原生 `sqlite3`，`PRAGMA user_version = 1`）

**Testing**: pytest + pytest-mock；unit tests 不得呼叫真實 API

**Target Platform**: Windows 10/11 桌面（PyInstaller --onedir 打包）

**Project Type**: desktop-app

**Performance Goals**: 冷啟動 < 3 秒；UI 頁面切換 < 300ms；30 檔股票盤後完整更新 < 10 分鐘

**Constraints**: FinMind 免費方案 600 req/hr（Token 啟用後）；Gemini 每日上限 50 次呼叫；追蹤股上限 30 檔；財務數值由 Python 計算，LLM 不得做數值運算

**Scale/Scope**: 單使用者本機桌面應用；30 檔追蹤股；5 張頁面；1 個背景更新管線

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Traceability Gate**: ✅ `market_events.source_url`、`fetched_at`；`financial_metrics.source_name`、`fetched_at`；`market_overviews.fetched_at` 均已設計。
- [x] **AI Boundary Gate**: ✅ `ISummarizationAgent` 僅做摘要 + 語意標記；`disclaimer` 欄位寫入 DB；LLM system prompt 明確禁止數值判斷與買賣建議。
- [x] **UI Decoupling Gate**: ✅ GUI 層僅呼叫 ViewModel；ViewModel 呼叫 Service；Service 呼叫 Repository / Agent；無從 UI 直接呼叫 FinMind / Gemini。
- [x] **MVP Scope Gate**: ✅ spec 的 Non-Goals 表格已標註 Phase 2/3；Future Considerations 標明 Extension Point，MVP 程式碼不實作。
- [x] **Testability Gate**: ✅ `contracts/service-interfaces.md` 定義所有 Service / Agent / Repository ABC；所有實作可被 Mock 替換。
- [x] **Fallback Gate**: ✅ `DataFetchError(retryable=True)` + UpdateJob 失敗狀態 + UI 顯示 retry 按鈕；離線時顯示最後 `fetched_at` 快取。
- [x] **Cost Gate**: ✅ FinMind 每日上限 800 req（FR-029）；Gemini 每日上限 50 次（app_settings.llm_daily_calls）；`UpdateJob.llm_tokens_used` 記錄每次用量。

## Project Structure

### Documentation (this feature)

```text
specs/001-midas-mvp/
├── plan.md              # This file
├── research.md          # Phase 0 研究結論
├── data-model.md        # SQLite schema + Python dataclasses
├── quickstart.md        # 開發環境快速入門
├── contracts/
│   └── service-interfaces.md   # Service / Agent / Repository ABCs
└── tasks.md             # Phase 2 output (由 /speckit.tasks 產生)
```

### Source Code (repository root)

```text
midas/
├── main.py                          # Entry point（啟動 CTk App）
├── pyproject.toml                   # uv 專案設定
├── .env.example                     # 環境變數範本
├── build.spec                       # PyInstaller 打包設定
├── scripts/
│   ├── load_fixtures.py             # 載入測試假資料至本機 DB
│   └── reset_db.py                  # 清除本機測試 DB
├── src/
│   └── midas/
│       ├── __init__.py
│       ├── app.py                   # App(ctk.CTk)：頁面 Router + queue 輪詢
│       ├── config.py                # AppConfig：路徑、環境變數讀取
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── app_window.py        # 主視窗：側邊欄 + 內容區 + 狀態列
│       │   ├── theme.py             # CTk 主題設定、顏色常數
│       │   ├── pages/
│       │   │   ├── __init__.py
│       │   │   ├── dashboard_page.py      # US-01: 盤後摘要看板
│       │   │   ├── stock_detail_page.py   # US-02/03: 個股詳情（事件 + 財務 Tab）
│       │   │   ├── watchlist_page.py      # US-04: 追蹤清單管理
│       │   │   ├── settings_page.py       # 設定頁（API Key、主題切換）
│       │   │   └── api_monitor_page.py    # API 監控（Gemini / FinMind 配額、手動更新觸發）
│       │   └── components/
│       │       ├── __init__.py
│       │       ├── sidebar_nav.py          # 左側導航列
│       │       ├── status_bar.py           # 底部狀態列（進度 + 更新時間）
│       │       ├── market_overview_card.py # 大盤概況卡（US-01）
│       │       ├── event_list_item.py      # 首頁事件清單行
│       │       ├── stock_event_card.py     # 個股詳情事件卡（含摘要、來源、免責聲明）
│       │       └── financial_metric_row.py # 財務指標行（含方向標示）
│       ├── viewmodels/
│       │   ├── __init__.py
│       │   ├── dashboard_vm.py        # 首頁資料整合（大盤 + 事件排序）
│       │   ├── stock_detail_vm.py     # 個股詳情（事件 + 財務）
│       │   └── watchlist_vm.py        # 追蹤清單 CRUD
│       ├── services/
│       │   ├── __init__.py
│       │   ├── interfaces.py          # Service ABCs（IWatchlistService 等）
│       │   ├── watchlist_service.py
│       │   ├── event_service.py
│       │   ├── financial_service.py
│       │   ├── market_service.py
│       │   └── update_service.py      # 判斷是否需要更新、啟動背景任務
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── interfaces.py          # Agent ABCs
│       │   ├── orchestrator.py        # Code-based 更新管線（非 LLM 驅動）
│       │   ├── market_agent.py        # 抓取大盤概況
│       │   ├── announcement_agent.py  # FinMind 新聞（TaiwanStockNews）抓取與分類
│       │   ├── financial_agent.py     # FinMind 財務資料抓取與計算
│       │   └── summarization_agent.py # Gemini 摘要生成（含配額控制）
│       ├── repositories/
│       │   ├── __init__.py
│       │   ├── interfaces.py          # Repository ABCs
│       │   ├── database.py            # SQLite 連線、schema 初始化、migration
│       │   ├── tracked_stock_repo.py
│       │   ├── market_event_repo.py
│       │   ├── financial_metric_repo.py
│       │   ├── market_overview_repo.py
│       │   └── update_job_repo.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── tracked_stock.py       # @dataclass TrackedStock
│       │   ├── market_event.py        # @dataclass MarketEvent + EventType enum
│       │   ├── financial_metric.py    # @dataclass FinancialMetric + MetricType enum
│       │   ├── market_overview.py     # @dataclass MarketOverview
│       │   └── update_job.py          # @dataclass UpdateJob
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── finmind_client.py      # FinMind API 封裝（股價、財務、新聞、交易日、三大法人）
│       │   ├── twse_client.py         # TWSE OpenAPI 封裝（市場指數、個股日行情）
│       │   └── gemini_client.py       # Gemini API 封裝（gemini-3.5-flash，配額追蹤）
│       └── tasks/
│           ├── __init__.py
│           └── background_worker.py   # threading.Thread + queue.Queue 管理器
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── test_financial_calculator.py  # 5 大指標計算邏輯 + ±5% 方向規則
    │   ├── test_event_classifier.py      # EventType 分類與優先級排序
    │   ├── test_cache_strategy.py        # 快取有效期判斷邏輯
    │   ├── test_update_orchestrator.py   # Orchestrator 流程（全 Mock）
    │   ├── test_watchlist_service.py     # CRUD + 30 檔上限 + 備忘 500 字
    │   └── test_summarization_quota.py   # 每日 50 次配額控制
    ├── integration/
    │   ├── test_sqlite_repos.py           # Repository 對真實 SQLite 測試
    │   └── test_finmind_client.py         # 對真實 FinMind API（需 token，CI skip）
    └── fixtures/
        ├── sample_finmind_financial.json  # 財務報表假資料
        ├── sample_finmind_price.json      # 股價假資料
        ├── sample_mops_announcement.html  # 舊版 MOPS 假 HTML（已不使用，保留供參考）
        └── sample_gemini_response.json    # Gemini API 假回應
```

## Architecture Layers

### 依賴方向（單向，不可逆）

```
UI (pages / components)
    ↓ 呼叫
ViewModel (dashboard_vm, stock_detail_vm, watchlist_vm)
    ↓ 呼叫
Service (event_service, financial_service, market_service, watchlist_service)
    ↓ 呼叫
Repository (market_event_repo, financial_metric_repo, ...)   ←→  SQLite DB
    ↑ 也被
Agent (orchestrator, market_agent, announcement_agent, ...)
    ↓ 呼叫
Integration (finmind_client, twse_client, gemini_client)  → External APIs
    ↑
BackgroundWorker (threading.Thread + queue.Queue)
    ↑ 啟動自
UpdateService
```

### 各層職責

| 層次 | 職責 | 禁止事項 |
|------|------|---------|
| **UI / Pages** | 顯示資料、接收使用者輸入、呼叫 ViewModel | 直接呼叫 Service / API / DB |
| **UI / Components** | 可重用 CTkFrame 元件 | 持有業務邏輯 |
| **ViewModel** | 將 Service 資料轉換為 UI 所需格式 | 直接存取 DB 或外部 API |
| **Service** | 業務邏輯（排序、驗證、快取判斷） | 直接操作 HTTP / SQLite |
| **Agent** | 外部資料抓取、LLM 呼叫、計算（Orchestrator 排程） | 自主決定流程（由 Orchestrator code-based 控制） |
| **Repository** | SQLite CRUD、upsert、快取有效期查詢 | 業務邏輯 |
| **Integration** | 外部 API / 爬蟲封裝（retry, rate limit） | 直接寫入 DB |
| **BackgroundWorker** | threading.Thread 生命週期 + queue.Queue 訊息傳遞 | 直接操作 UI |

---

## Data Flow

### 啟動流程（冷啟動目標 < 3 秒）

```
main.py
  └─ App.__init__()
       ├─ 1. config.py 載入環境變數（APPDATA 路徑、API keys）
       ├─ 2. database.py 確認 DB 存在、執行 migration（< 100ms）
       ├─ 3. 初始化所有 Repository / Service / ViewModel 實例
       ├─ 4. 建立 UI（CTk 視窗、側邊欄、頁面 Frame）並顯示首頁
       ├─ 5. App.after(0, check_queue)  ← 啟動 queue 輪詢
       └─ 6. UpdateService.check_needs_update()
              ├─ 若需要更新（收盤後 ≥ 15:00 且今日無資料）
              │    └─ BackgroundWorker.start(orchestrator.run)
              └─ 若不需要（有快取）
                   └─ 直接顯示快取資料
```

### 盤後更新管線（Orchestrator，code-based）

```
orchestrator.run(symbols=[...30 隻...])
  │
  ├─ Step 1: MarketAgent.fetch_overview(today)
  │    └─ FinMindClient.get_market_data()
  │         → 加權指數、成交量、三大法人
  │    └─ MarketOverviewRepo.upsert()
  │
  ├─ Step 2: for each symbol:  AnnouncementAgent.fetch_announcements(symbol, today)
  │    └─ FinMindClient.get_stock_news(symbol, today)
  │         → TaiwanStockNews JSON → EventType 分類 → MarketEvent 列表
  │    └─ MarketEventRepo.upsert_many()
  │    └─ queue.put(("progress", {step, total, label}))
  │
  ├─ Step 3: for each symbol (if cache expired):  FinancialAgent.fetch_and_calculate(symbol)
  │    └─ FinMindClient.get_financial_statements(symbol)
  │    └─ Python 計算 EPS / 毛利率 / ROE / 負債比 / FCF + ±5% 方向
  │    └─ FinancialMetricRepo.upsert_many()
  │    └─ queue.put(("progress", ...))
  │
  ├─ Step 4: for each symbol with events (up to 50 LLM calls):
  │    └─ SummarizationAgent.summarize_events(symbol, events)
  │         └─ GeminiClient.generate(system_prompt, batch_text)
  │              → JSON {event_id: {summary, sentiment}} 
  │         └─ 驗證：無買賣建議、符合 80–800 字（含【新聞摘要】+【分析解讀】結構化格式）
  │         └─ MarketEventRepo.upsert_many(updated events)
  │         └─ UpdateJobRepo.update_progress(llm_calls, tokens)
  │
  └─ Step 5: UpdateJobRepo.complete()
       └─ queue.put(("update_complete", UpdateJob))
```

### UI 接收更新訊息

```
App.check_queue()  [每 500ms，主執行緒]
  ├─ ("progress", payload)  → StatusBar.update_progress(step, total, label)
  ├─ ("update_complete", job)  → DashboardPage.refresh()
  └─ ("update_error", msg)  → StatusBar.show_error(msg) + retry button
```

### 使用者點擊個股詳情

```
DashboardPage: 點選 EventListItem
  └─ controller.show_frame(StockDetailPage, symbol=symbol)
       └─ StockDetailPage.load(symbol)
            └─ StockDetailViewModel.load_events(symbol, today)
                 └─ EventService.get_events_for_stock(symbol, today)
                      └─ MarketEventRepo.get_by_symbol_date()  [從 SQLite，無網路]
            └─ StockDetailViewModel.load_metrics(symbol)
                 └─ FinancialService.get_metrics(symbol, quarters=12)
                      └─ FinancialMetricRepo.get_by_symbol()  [從 SQLite]
```

---

## Integration Strategy

### FinMind Client

```python
# 關鍵設計決策
class FinMindClient:
    MAX_REQUESTS_PER_HOUR = 600     # Token 啟用後
    RETRY_MAX = 3
    RETRY_WAIT_429 = 60             # 秒（限流後等待）
    BACKOFF_BASE = 2                # 指數退避基數

    # 每次請求前：
    # 1. 檢查今日累計請求數（來自 UpdateJob）
    # 2. 若預估本次更新將超過 800 次，中止並記錄 partial 狀態
    # 3. HTTP 429 → 等待 60s → 重試（最多 3 次）
    # 4. HTTP 5xx → 指數退避重試
    # 5. 所有請求 timeout=15s
```

**Dataset 請求估算**（30 檔，每日）：
- MarketOverview: 3 次（指數、三大法人、類股）
- Announcements: 30 次（FinMind TaiwanStockNews，每股 1 次 REST 請求）
- Financial（cache miss，估計 10 檔/日）: 5 datasets × 10 = 50 次
- 合計估算：~83 次/日 ✅（遠低於 800 次上限）

### FinMind 新聞抓取（AnnouncementAgent）

```python
# FinMindClient.get_stock_news(symbol, date) 直接呼叫 REST API
# endpoint: https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockNews
# 回傳欄位：title, description, link, source, date, stock_id
# EventType 分類根據 title 關鍵字：
# - 含「財報/季報/盈餘/EPS」→ financial_report
# - 含「法說/法人說明會」→ investor_conference
# - 含「重大訊息/合併/收購」→ material_news
# - 其他 → general_announcement
```

### Gemini Client

```python
class GeminiClient:
    MODEL = "gemini-3.5-flash"
    DAILY_CALL_LIMIT = 50
    
    # System prompt 要求以長期投資視角分析，固定輸出兩段格式：
    # 【新聞摘要】：2–3 句概括事實
    # 【分析解讀】：①事件性質 ②長期基本面 ③風險
    # 規則：
    # - sentiment 依「長期基本面」判斷，非短期股價情緒
    # - 禁止買進 / 賣出 / 持有等投資建議
    # - 禁止虛構數字，推測須標示「推測」或「不確定」
    # 輸出：純 JSON（不含 Markdown code fence）
    # {"events": [{"id": <int>, "summary": <str>, "sentiment": "positive|neutral|negative"}]}
    
    # 摘要驗證（_apply_summaries）：80 ≤ len(summary) ≤ 800
    
    # 配額控制：
    # 呼叫前：讀取 app_settings.llm_daily_calls
    # 若 >= 50 且日期 = 今日 → 拋出 LLMQuotaExceededError
    # 呼叫後：更新 llm_daily_calls + llm_daily_date + UpdateJob.llm_tokens_used
```

---

## GUI Design

### 主視窗佈局

```
┌─────────────────────────────────────────────────────────┐
│  AppWindow (CTk 視窗, 1280×800, 深色模式預設)           │
│  ┌──────────────┬────────────────────────────────────┐  │
│  │  SidebarNav  │  ContentArea (CTkFrame 容器)        │  │
│  │  (180px)     │  ┌────────────────────────────────┐│  │
│  │  • 首頁      │  │  DashboardPage  (預設)          ││  │
│  │  • 追蹤清單  │  │  StockDetailPage                ││  │
│  │  • API 監控  │  │  WatchlistPage                  ││  │
│  │  • 設定      │  │  ApiMonitorPage                 ││  │
│  │              │  │  SettingsPage                   ││  │
│  │              │  └────────────────────────────────┘│  │
│  └──────────────┴────────────────────────────────────┘  │
│  StatusBar (28px)  [最後更新: 2026-05-19 16:30]  [進度] │
└─────────────────────────────────────────────────────────┘
```

### 頁面模組對應

| 頁面 | 主要元件 | ViewModel | 對應 US |
|------|---------|-----------|---------|
| `DashboardPage` | `MarketOverviewCard` + `EventListItem` 列表 | `DashboardViewModel` | US-01 |
| `StockDetailPage` | Tab: `StockEventCard` 列表 / `FinancialMetricRow` 列表 | `StockDetailViewModel` | US-02, US-03 |
| `WatchlistPage` | 追蹤股清單 + 新增/刪除/備忘 | `WatchlistViewModel` | US-04 |
| `ApiMonitorPage` | Gemini 每日配額進度、FinMind 本輪請求數、上次更新記錄、手動更新按鈕 | —（直接讀 GeminiClient + FinMindClient + UpdateJobRepo） | US-05 |
| `SettingsPage` | API Key 輸入、主題切換、清除快取 | — | 設定 |

### 首頁事件清單排序規則（UI 層無需自行排序）

`DashboardViewModel.get_today_events()` 回傳已排序清單：
1. 有事件的追蹤股（按 `event_type_priority ASC`，`occurred_at DESC`）
2. 無事件的追蹤股（淡色顯示，按 `company_name ASC`）

---

## Testing & Quality

### 單元測試範圍（不呼叫真實 API）

| 測試檔 | 測試對象 | Mock 對象 |
|-------|---------|---------|
| `test_financial_calculator.py` | `FinancialAgent._calculate_metrics()` | FinMindClient |
| `test_event_classifier.py` | `AnnouncementAgent._classify_event()` | FinMindClient（mock） |
| `test_cache_strategy.py` | `FinancialMetricRepo.is_cache_valid()` | DB（in-memory SQLite） |
| `test_update_orchestrator.py` | `Orchestrator.run()` 流程控制 | 所有 4 個 Agent |
| `test_watchlist_service.py` | `WatchlistService` CRUD + 驗證 | TrackedStockRepo |
| `test_summarization_quota.py` | `SummarizationAgent` 配額邏輯 | GeminiClient |

### 整合測試範圍（標記 `@pytest.mark.integration`，CI 跳過）

- `test_sqlite_repos.py`：對真實 in-memory SQLite 測試所有 repo CRUD
- `test_finmind_client.py`：對真實 FinMind API（需設定 FINMIND_TOKEN）

### Fixture 策略

- `fixtures/sample_finmind_financial.json`：仿 FinMind API 回應格式（含 4 個 dataset）
- `fixtures/sample_mops_announcement.html`：舊版 MOPS 假 HTML（已不使用，保留供參考）
- `fixtures/sample_gemini_response.json`：含 events 摘要 JSON

### 打包前最低驗收標準

- [ ] `pytest tests/unit/` 全綠（0 failures）
- [ ] 冷啟動至首頁顯示 < 3 秒（空 watchlist）
- [ ] 新增 1 筆追蹤股 → 重啟 → 資料保留
- [ ] 手動觸發更新（ApiMonitorPage）→ 狀態列顯示進度 → 完成後首頁刷新
- [ ] 關閉應用後 `midas.db` 存在於 `%APPDATA%\Midas\`

---

## Non-Functional Requirements Mapping

| NFR | 技術方案 |
|-----|---------|
| 冷啟動 < 3 秒 | DB migration 在啟動時執行（< 100ms）；頁面 Frame 預先建立；首頁顯示快取資料不等待 API |
| 頁面切換 < 300ms | `tkraise()` 切換（不 destroy/recreate）；ViewModel 資料預先載入 |
| 盤後更新 < 10 分鐘 | 30 檔股票；Step 2（MOPS）串行抓取含 500ms 間隔預估 30 × 1s = 30s；Step 3（財務，cache miss 10 檔）= ~20s；Step 4（LLM，30 次 × 2s） = ~60s；總計 < 3 分鐘 |
| 資料附來源與時間戳 | 所有 dataclass 強制 `source_name` + `fetched_at` 欄位；Repository upsert 時不可省略 |
| AI 結論附免責聲明 | `market_events.disclaimer` 寫入 DB；`StockEventCard` component 無條件顯示 |
| 背景更新不阻塞 UI | `threading.Thread(daemon=True)` + `queue.Queue` + `App.after(500, check_queue)` |
| 失敗可見 + 可重試 | `UpdateJob.status='failed'` + `queue.put(("update_error", msg))` → `StatusBar.show_error()` + retry button |
| LLM 不做數值計算 | System prompt 明確禁止；所有財務數值在 `FinancialAgent` 由 pandas / Python 計算後，只以文字描述傳給 LLM |
| 成本可控 | FinMind 每日 800 req 限制（FR-029）；Gemini 每日 50 calls 配額（app_settings）；每次呼叫記錄 token 數 |

---

## Phase 2 / Phase 3 Extension Points

以下介面已預留，MVP 程式碼**不實作**，不封閉這些路徑：

| 擴充功能 | Extension Point | MVP 現況 |
|---------|----------------|---------|
| 評價分析 | `FinancialMetric` 可加入 P/E、P/B 等 `metric_type` 值 | 僅 5 種指標 |
| 法說摘要頁 | `EventType.investor_conference` 已定義；`SummarizationAgent` 支援長文輸入 | 與其他事件混合顯示 |
| 研究筆記 | `TrackedStock.memo` 升級為獨立 `notes` 表（外鍵）的路徑已設計 | 純文字備忘欄位 |
| 智慧提醒 | `UpdateJob` 完成後可觸發「重要事件」訊號；`IUpdateService` 介面可擴充 callback | 無通知功能 |
| 產業地圖 | `MarketOverview.sector_rankings` JSON 保留原始類股代碼 | 純文字清單 |
| 社群輿情 | `MarketEvent.source_name` 欄位支援非 MOPS 來源；`sentiment_source` 可加入 | 僅 MOPS 來源 |
| 排程常駐更新 | `UpdateService` / `BackgroundWorker` 介面不依賴「應用開啟」狀態，可升級為 Task Scheduler | 啟動時觸發 |

