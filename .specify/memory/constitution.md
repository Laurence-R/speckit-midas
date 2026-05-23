<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 -> 1.1.0
Modified principles:
  - I. 資料可溯源優先 (Data Traceability First) -> I. 資料可溯源優先 (Data Traceability First) [clarified source mapping fallback]
  - II. AI 僅輔助，不可取代判斷 (AI Assists, Never Replaces Judgment) -> II. AI 僅輔助，不可取代判斷 (AI Assists, Never Replaces Judgment) [clarified LLM workflow boundary]
  - III. 桌面體驗穩定優先 (Desktop UI Stability First) -> III. 桌面 UI 框架與體驗穩定優先 (Desktop UI and Stability First) [expanded CustomTkinter mandates]
  - V. 架構必須可測試、可替換 (Testable and Replaceable Architecture) -> V. 架構邊界必須可測試、可替換 (Bounded, Testable, Replaceable Architecture) [expanded dependency and import constraints]
  - VI. 在地桌面產品原則 (Local-First Desktop Product) -> VI. 在地桌面產品原則 (Local-First Desktop Product) [expanded SQLite schema/offline fallback]
  - VII. 成本與可控性優先 (Cost and Controllability First) -> VII. 資料供應商治理與成本可控性優先 (Provider Governance and Cost Controllability First) [expanded FinMind governance]
Added sections:
  - 專案定位
Removed sections:
  - none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated
  - .specify/templates/spec-template.md ✅ updated
  - .specify/templates/tasks-template.md ✅ updated
  - .specify/extensions/git/commands/*.md ✅ reviewed (no outdated agent-specific references)
Deferred TODOs:
  - none
-->

# Midas Constitution

## 專案定位

Midas 是一套運行於 Windows 10/11 的台股盤後投研桌面工具。

- 產品目標 MUST 聚焦於盤後研究效率與資訊可信度。
- 核心能力 MUST 支援本機優先使用情境，不以雲端綁定作為前提。
- 所有功能擴充 MUST 不得破壞本憲章所定義的投研產品原則與工程治理邊界。

## Core Principles

### I. 資料可溯源優先 (Data Traceability First)

每個資料點、事件摘要、財務指標及 AI 結論都 MUST 附帶**來源名稱與時間戳**。

- 使用者 MUST 能存取原始來源連結；不可只呈現 AI 結論。
- 所有分析流程 MUST 可追蹤，禁止黑箱輸出。
- 若資料點無法標注來源，MUST 以明確的「來源未知」標籤替代，不可靜默省略。
- Repository 層在儲存每筆資料時，MUST 同步寫入 `source_url`、`fetched_at` 欄位。
- 若採用非 FinMind 替代資料源，MUST 在 spec/plan 記錄欄位對映、可信度評估與 fallback 策略。

**Rationale**: 基本面投資決策影響真實資金；無可追溯的資訊等同不可信的資訊。

### II. AI 僅輔助，不可取代判斷 (AI Assists, Never Replaces Judgment)

LLM 的職責 MUST 限定於摘要、分類、重點提煉與語意標記。

- 所有 AI 摘要與分析旁 MUST 附免責聲明：「此為 AI 摘要，僅供參考，不構成投資建議。」
- EPS、毛利率、ROE、負債比、自由現金流等財務數值 MUST 由 Python 程式計算後，
  再交由 LLM 解讀；LLM 不可負責數值運算。
- LLM 不可輸出任何形式的「買進」「賣出」「持有」直接建議。
- Agent 呼叫 LLM 時 MUST 傳入 system prompt 明確限制角色邊界。
- LLM 僅可讀取經 Service 層整理後的結構化資料，MUST NOT 直接決定工作流程或數值結果。

**Rationale**: 防止 LLM 幻覺污染財務數值；保護使用者免受錯誤的 AI 投資建議。

### III. 桌面 UI 框架與體驗穩定優先 (Desktop UI and Stability First)

背景資料更新 MUST NOT 阻塞 UI 主執行緒。

- 桌面 UI MUST 使用 Python + CustomTkinter。
- 主視窗 MUST 使用 `customtkinter.CTk`。
- 畫面元件 SHOULD 以 `CTkFrame` 作為可重用畫面單位。
- UI 元件 MUST 使用 CustomTkinter 元件族（如 `CTkButton`、`CTkEntry`、`CTkLabel`、`CTkTextbox`），
  除非有明確相容性理由並記錄於 ADR，否則 MUST NOT 混用原生 tkinter/ttk。
- 視覺主題 MUST 支援深色模式優先，並提供亮色模式切換。
- 頁面切換 MUST 在 200 ms 內完成響應（不含資料載入）。
- 任何網路失敗、API 限流、爬蟲錯誤都 MUST 呈現可見錯誤狀態，並提供可重試機制。
- UI 層 MUST NOT 直接呼叫外部 API 或執行 I/O；所有資料取得須透過 Service 層。
- 離線狀態 MUST 回退顯示最後快取資料，並標注資料的 `fetched_at` 時間戳。

**Rationale**: 桌面應用的信任感建立在穩定與可預期的體驗，而非功能堆疊。

### IV. MVP 範圍嚴格控管 (Strict MVP Scope Discipline)

MVP MUST 僅包含：盤後摘要、自選追蹤、個股事件詳情、財務健康快覽、大盤概況、自動更新。

- Phase 2（回測、選股篩選）與 Phase 3（社群協作、推播通知）功能 MUST NOT
  混入 MVP 實作，除非明確標註為擴充點（Extension Point）且有功能開關保護。
- 每個任務拆解 MUST 支援至少一條可獨立驗證的垂直切片（Vertical Slice）。
- 凡不在上述 MVP 清單的需求，MUST 在 spec 中標註 `[OUT OF SCOPE - Phase N]`。

**Rationale**: 明確的邊界讓 MVP 可在有限週期內交付，並驗證核心價值假設。

### V. 架構邊界必須可測試、可替換 (Bounded, Testable, Replaceable Architecture)

UI、業務邏輯、資料存取、外部 API 整合 MUST 解耦為獨立層次。

- 依賴方向 MUST 為單向：`UI -> ViewModel/Presenter -> Service -> Repository -> External Provider`。
- 每個 Service、Agent、Repository MUST 具備明確的介面定義（Protocol/ABC），
  以支援單元測試與 Mock 替換。
- UI 層 MUST NOT 直接 import FinMind SDK、requests、sqlite driver 或其他外部 I/O 模組。
- 所有外部資料抓取、清洗、欄位標準化、快取回退 MUST 在 Service/Repository 層處理。
- 新功能 MUST 在 Service 層提供對應的單元測試入口。

**Rationale**: 可替換性確保 FinMind、LLM 供應商、資料源變更不會導致大規模重寫。

### VI. 在地桌面產品原則 (Local-First Desktop Product)

MVP MUST 以 Windows 10/11 為主要目標平台。

- 本機資料 MUST 儲存於 SQLite。
- 應用 MUST 預設啟用深色模式，並提供亮色模式切換選項。
- Windows 本機資料目錄 MUST 遵循 `%APPDATA%\Midas` 慣例。
- 使用者設定、自選股、快取、摘要歷史、token 用量記錄 SHOULD 具備明確資料表或 schema 規劃。
- 核心功能 MUST 支援離線回退顯示最後可用快取，並標示 `fetched_at`。
- 不可要求使用者強制登入雲端帳號方可使用核心功能。

**Rationale**: 本機優先架構降低隱私顧慮，減少雲端依賴，提升離線可用性。

### VII. 資料供應商治理與成本可控性優先 (Provider Governance and Cost Controllability First)

Agent Orchestration MUST 採用 code-based orchestration，禁止由 LLM 自主決策工作流程。

- 台股市場資料、歷史股價、基本面與事件資料 MUST 優先使用 FinMind 作為主要資料來源。
- FinMind 存取 MUST 透過統一的 Service/Repository 封裝，UI 層不可直接呼叫。
- Python 端 SHOULD 優先採用官方推薦用法（例如 `from FinMind.data import DataLoader`）。
- FinMind 驗證機制 MUST 使用 token-based login，敏感資訊不得硬編碼於程式碼。
- 批次抓取與本機快取 MUST 優先於即時 API 呼叫，以降低 FinMind 與 LLM API 成本。
- 若外部資料來源或 LLM 呼叫失敗，系統 MUST 回退至最後可用快取，
  MUST NOT 中斷主畫面的顯示流程。
- 每次 LLM 呼叫 MUST 記錄 token 用量與時間戳，供後續成本審計。
- 高頻資料抓取 MUST 使用排程機制（盤後單次觸發），禁止無限輪詢。

**Rationale**: 個人投研工具的長期可持續性取決於可控且可預期的運行成本。

## MVP Boundaries

**In Scope (MVP)**:
- 盤後大盤概況（加權指數、成交量、漲跌家數）
- 自選股追蹤清單（新增、刪除、排序）
- 個股事件詳情（重大訊息、法說會摘要、財報事件）
- 財務健康快覽（EPS、毛利率、ROE、負債比、自由現金流）
- AI 事件摘要（附來源、免責聲明）
- 盤後自動更新觸發機制
- 本機 SQLite 快取與筆記

**Out of Scope (Phase 2+)**:
- 回測引擎、策略模擬
- 選股篩選條件設定
- 推播通知 / 行動裝置同步
- 社群協作 / 分享功能
- 雲端同步帳號系統

## Quality Gates

每個 spec 與 plan 在進入實作前 MUST 通過以下檢查：

1. **Traceability Gate**: 所有資料欄位設計是否包含 `source_url` 與 `fetched_at`？
2. **AI Boundary Gate**: LLM 呼叫是否限定在摘要/分類/標記，且附有免責聲明？
3. **UI Decoupling Gate**: UI 是否透過 ViewModel/Service 層取得資料，無直接外部呼叫？
4. **MVP Scope Gate**: 本 spec 的需求是否全數在 MVP 清單內，或已明確標註 Phase N？
5. **Testability Gate**: 每個 Service 與 Repository 是否有明確介面可供 Mock？
6. **Fallback Gate**: 網路失敗路徑是否有快取回退與可見錯誤狀態設計？
7. **Cost Gate**: LLM 與外部 API 呼叫是否有頻率控制與 token 記錄設計？
8. **Desktop Framework Gate**: 是否明確遵守 CustomTkinter 為唯一主要 GUI 框架？
9. **Provider Boundary Gate**: 是否所有 FinMind 呼叫都經 Service/Repository，而非 UI？
10. **Secrets Gate**: token、API key、路徑設定是否避免硬編碼？
11. **Local-First Gate**: 是否具備 SQLite 快取、離線 fallback、`fetched_at` 顯示？
12. **Source Mapping Gate**: 若使用非 FinMind 資料源，是否定義欄位映射與可信度說明？

## Governance

本憲章是 Midas 專案所有 spec、plan、tasks 的最高品質標準文件。

- 所有 PR / Code Review MUST 驗證與憲章原則的一致性。
- 任何原則修訂 MUST 更新版本號、`Last Amended` 日期，並記錄修訂原因。
- 版本號遵循語意化版本：
  - **MAJOR**: 原則刪除或不相容重定義
  - **MINOR**: 新增原則或章節、實質性擴充
  - **PATCH**: 文字澄清、措辭修正、非語意調整
- `plan-template.md` 的 Constitution Check 章節 MUST 與本憲章的 Quality Gates 保持同步。
- 若原則與實際需求產生衝突，MUST 先修訂憲章再進行實作，不可直接繞過。

**Version**: 1.1.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-23
