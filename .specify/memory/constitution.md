<!--
SYNC IMPACT REPORT
==================
Version change: (new) → 1.0.0
Added sections:
  - Core Principles (7 principles defined)
  - MVP Boundaries
  - Quality Gates
  - Governance
Templates updated:
  - .specify/templates/plan-template.md ✅ — Constitution Check gates updated
  - .specify/templates/spec-template.md ✅ — No structural change required
  - .specify/templates/tasks-template.md ✅ — No structural change required
Deferred TODOs: none
-->

# Midas Constitution

## Core Principles

### I. 資料可溯源優先 (Data Traceability First)

每個資料點、事件摘要、財務指標及 AI 結論都 MUST 附帶**來源名稱與時間戳**。

- 使用者 MUST 能存取原始來源連結；不可只呈現 AI 結論。
- 所有分析流程 MUST 可追蹤，禁止黑箱輸出。
- 若資料點無法標注來源，MUST 以明確的「來源未知」標籤替代，不可靜默省略。
- Repository 層在儲存每筆資料時，MUST 同步寫入 `source_url`、`fetched_at` 欄位。

**Rationale**: 基本面投資決策影響真實資金；無可追溯的資訊等同不可信的資訊。

### II. AI 僅輔助，不可取代判斷 (AI Assists, Never Replaces Judgment)

LLM 的職責 MUST 限定於摘要、分類、重點提煉與語意標記。

- 所有 AI 摘要與分析旁 MUST 附免責聲明：「此為 AI 摘要，僅供參考，不構成投資建議。」
- EPS、毛利率、ROE、負債比、自由現金流等財務數值 MUST 由 Python 程式計算後，
  再交由 LLM 解讀；LLM 不可負責數值運算。
- LLM 不可輸出任何形式的「買進」「賣出」「持有」直接建議。
- Agent 呼叫 LLM 時 MUST 傳入 system prompt 明確限制角色邊界。

**Rationale**: 防止 LLM 幻覺污染財務數值；保護使用者免受錯誤的 AI 投資建議。

### III. 桌面體驗穩定優先 (Desktop UI Stability First)

背景資料更新 MUST NOT 阻塞 UI 主執行緒。

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

### V. 架構必須可測試、可替換 (Testable and Replaceable Architecture)

UI、業務邏輯、資料存取、外部 API 整合 MUST 解耦為獨立層次。

- 依賴方向 MUST 為單向：`UI → ViewModel/Presenter → Service → Repository → External`。
- 每個 Service、Agent、Repository MUST 具備明確的介面定義（Protocol/ABC），
  以支援單元測試與 Mock 替換。
- GUI MUST NOT 直接匯入或呼叫任何外部 API SDK 或資料庫存取模組。
- 新功能 MUST 在 Service 層提供對應的單元測試入口。

**Rationale**: 可替換性確保 FinMind、LLM 供應商、資料源變更不會導致大規模重寫。

### VI. 在地桌面產品原則 (Local-First Desktop Product)

MVP MUST 以 Windows 10/11 為主要目標平台。

- 追蹤清單、快取資料與使用者筆記 MUST 儲存於本機 SQLite 資料庫。
- 應用 MUST 預設啟用深色模式，並提供亮色模式切換選項。
- 本機資料路徑 MUST 遵循 Windows 的 `%APPDATA%\Midas` 慣例。
- 不可要求使用者強制登入雲端帳號方可使用核心功能。

**Rationale**: 本機優先架構降低隱私顧慮，減少雲端依賴，提升離線可用性。

### VII. 成本與可控性優先 (Cost and Controllability First)

Agent Orchestration MUST 採用 code-based orchestration，禁止由 LLM 自主決策工作流程。

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

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
