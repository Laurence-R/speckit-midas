# Research: Midas MVP 技術選型

**Phase**: 0 — Pre-Design Research
**Date**: 2026-05-19
**Feature**: [spec.md](spec.md)

## R-01 CustomTkinter 多頁架構

**Decision**: Controller + CTkFrame subclass pattern，以 `tkraise()` 切換頁面

**Findings**:
- 使用 `App(ctk.CTk)` 作為 Controller，持有所有 Page frame 的字典
- 每個 Page 繼承 `ctk.CTkFrame`，建構時接收 `controller` 參考
- `show_frame()` 呼叫 `frame.tkraise()` 切換——不 destroy/recreate，避免重建成本
- 頁面切換實測 < 50ms（30 個 widget 以內）

**Alternatives rejected**:
- ❌ 每次 destroy + recreate frame：重建大型 layout 耗時 200–500ms
- ❌ 全域函式 routing：無法 mock controller，測試困難

## R-02 Background Thread ↔ UI 通訊

**Decision**: `queue.Queue` + `app.after(500, check_queue)` polling

**Findings**:
- `queue.Queue` 是 thread-safe（GIL 保障），可安全跨執行緒寫入
- 主執行緒以 `.after(500, ...)` 每 500ms 輪詢一次，不阻塞事件迴圈
- 訊息格式：`(event_type: str, payload: Any)` tuple
- 更新進度：`("progress", {"step": 2, "total": 6, "label": "抓取財務資料..."})` 

**Alternatives rejected**:
- ❌ Tkinter variable trace：不跨執行緒安全
- ❌ asyncio：Tkinter 事件迴圈非 async-native，整合複雜

## R-03 可執行檔打包策略（Deferred）

**Decision**: 目前版本不納入打包流程；保留歷史研究結論供後續版本恢復時參考。

**Findings**:
- `--onefile` 每次啟動需解壓至 temp，冷啟動額外增加 2–3 秒，且易觸發 Windows Defender
- `--onedir` 啟動快，分發時打包整個 dist/ 資料夾即可
- 必要 hidden imports: `customtkinter`, `PIL`, `google.generativeai`, `finmindapi`
- `console=False` 避免 cmd 視窗出現
- UTF-8 設定 (`win_private_codepage`) 對應繁中輸出

## R-04 FinMind API 資料集對應

**Decision**: 使用 FinMind Python SDK（`FinMind.data.DataLoader`），以 Token 登入取得 600 req/hr

| MVP 功能 | Dataset ID | 備註 |
|---------|-----------|------|
| 股票基本資訊（代號 → 公司名） | `TaiwanStockInfo` | 一次性快取，長期有效 |
| 每日收盤價 / 成交量 | `TaiwanStockPrice` | 大盤概況用 |
| 三大法人買賣超 | `TaiwanStockInstitutionalInvestorsBuySell` | 大盤概況用 |
| EPS | `TaiwanStockFinancialStatements` (type='EPS') | 直接取值 |
| 毛利率 | `TaiwanStockFinancialStatements` | GrossProfit / (GP + COGS) 計算 |
| ROE | `TaiwanStockFinancialStatements` + `BalanceSheet` | 跨兩個 dataset 計算 |
| 負債比 | `TaiwanStockBalanceSheet` | TotalLiabilities / TotalAssets 計算 |
| 自由現金流 | `TaiwanStockCashFlowsStatement` | OperatingCF - CapEx 計算 |

**Rate limit**: 免費方案 300 req/hr；使用 Token 後 600 req/hr。30 檔股票每日盤後更新估計約 250–400 次請求（含財務歷史查詢）。

**Caching rule**: 事件資料使用當日快取；財務資料在盤後更新時每次重抓（不採 7 天門控）。

## R-05 MOPS 公告爬蟲策略（Legacy）

**Decision**: 不採用。已改為 FinMind TaiwanStockNews。

**Historical findings**:
- MOPS 以 form POST 方式提供重大訊息查詢（非 REST API）
- 重大訊息 endpoint: `https://mops.twse.com.tw/mops/web/t05st010`
- 財報公告 endpoint: `https://mops.twse.com.tw/mops/web/t57sb01`
- 回應為 UTF-8 HTML（非 Big5），`BeautifulSoup('html.parser')` 可直接解析
- 無 session/cookie 需求；建議 500ms 請求間隔避免 403
- 無需 Selenium（頁面非 JS 動態渲染）

**Note**:
- 本段僅保留歷史比較脈絡，現行實作不含 MOPS 爬蟲程式碼。

## R-06 Gemini API 摘要策略

**Decision**: `gemini-3.5-flash`，每股批次一次呼叫（合併當日所有事件）

**Findings**:
- Free tier: 5 req/min，250K tokens/min, 20 req/day
- 單次摘要成本：約 $0.000085（500 字公告 → 結構化【新聞摘要】+【分析解讀】摘要）
- 30 檔股票每日上限 50 次呼叫 → 約 60–70% 有事件的股票能取得摘要
- System prompt 以長期投資視角分析，輸出固定【新聞摘要】+【分析解讀】①②③ 格式；禁止買賣建議
- 摘要驗證範圍：80–800 字（由程式碼層驗證，非 DB 約束）
- 每次呼叫後記錄 `usage_metadata.total_token_count` 至 UpdateJob

**Batching strategy**: 每股票一次呼叫，將當日所有事件文字合併傳入，輸出 JSON 格式（含各事件摘要 + sentiment）

## R-07 SQLite + 本機儲存路徑

**Decision**: 原生 `sqlite3`（不引入 SQLAlchemy 降低依賴複雜度），路徑 `%APPDATA%\Midas\midas.db`

**Findings**:
- Python 內建 `sqlite3` 足以應付 MVP 單機使用場景
- `%APPDATA%` → `os.path.expandvars('%APPDATA%')` 或 `platformdirs.user_data_dir('Midas')`
- 使用 `check_same_thread=False` + 應用層 mutex 確保背景執行緒安全寫入
- Migration: 以手動版本號控制（`PRAGMA user_version`），MVP 僅一個 schema 版本

## Summary of Key Decisions

| 決策項目 | 選定方案 | 主要理由 |
|---------|---------|---------|
| UI 架構 | Controller + CTkFrame + tkraise() | 效能佳、可測試 |
| 背景通訊 | queue.Queue + after() polling | Thread-safe、無需 asyncio |
| 打包 | Deferred（保留 PyInstaller 研究） | 目前以原始碼執行為主，後續版本再納入 |
| FinMind | SDK + Token，事件日內快取 + 財務每次重抓 | 免費方案配額管理 |
| MOPS | ~~requests + BS4~~ → 改用 FinMind TaiwanStockNews | FinMind 已提供新聞 API，無需爬蟲 |
| LLM | gemini-3.5-flash，每股批次 | 效能與成本平衡 |
| DB | 原生 sqlite3，PRAGMA user_version | 零依賴、夠用 |
