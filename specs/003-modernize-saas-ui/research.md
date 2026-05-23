# Research: Modernize SaaS UI Tone and Layout

**Phase**: 0 - Pre-Design Research  
**Date**: 2026-05-23  
**Feature**: [spec.md](spec.md)

## Decision 1: 採用語意化色彩角色而非元件硬編碼色值

**Decision**: 以語意化角色（例如 `bg_primary`, `text_primary`, `accent`, `success`, `warning`, `error`）管理雙主題配色，所有頁面與元件僅使用語意角色，不直接寫死 HEX。

**Rationale**:
- 可確保深色/亮色主題切換時風格一致。
- 降低頁面改版時的局部偏色與維護成本。
- 對應現有 `src/midas/ui/theme.py` 結構，改動風險可控。

**Alternatives considered**:
- 逐檔案直接替換 HEX：速度快但容易產生遺漏與風格漂移。
- 每個元件自帶配色：彈性高但會破壞跨頁一致性與可治理性。

## Decision 2: 採用中高密度版面策略並以 spacing token 驗收

**Decision**: 採用中高密度（資訊效率優先、保留必要呼吸感），建立全站 spacing token 級距（S/M/L）作為唯一留白驗收基準。

**Rationale**:
- 已由 clarify 確認需求核心為「避免過多留白」但不可擁擠。
- token 化可讓設計審查與開發驗收具可追溯依據。
- 可在不改動資料流程下，單純透過 UI 排版完成需求。

**Alternatives considered**:
- 純主觀視覺評審：無法穩定重複驗收。
- 只限制特定頁面：會造成跨頁排版節奏不一致。

## Decision 3: 文字對比採 WCAG AA 驗收閾值

**Decision**: 所有文字對比以 WCAG AA 為最低門檻：一般文字 >= 4.5:1，較大文字 >= 3:1。

**Rationale**:
- 需求已明確指定此標準，且可量化。
- 在深色與亮色模式都能提供一致的可讀性底線。
- 可作為回歸檢查項目，防止後續改色破壞可讀性。

**Alternatives considered**:
- 不設明確比率：驗收標準模糊。
- 全面 AAA（7:1）：限制過強，對品牌/視覺表現彈性不利。

## Decision 4: 深色與亮色模式同步改版

**Decision**: 本次同時完成深色與亮色模式的主題升級，並要求兩種模式在色彩語言、狀態語意與排版節奏一致。

**Rationale**:
- clarify 已明確要求雙模式同步。
- 符合憲法「深色優先且提供亮色切換」原則。
- 可避免後續以「臨時亮色」造成維護負擔。

**Alternatives considered**:
- 僅改深色模式：會造成亮色體驗落差與品質不一致。
- 先深色後亮色：短期可行但不符合本次完成定義。

## Decision 5: 視覺改版不得跨越資料與架構邊界

**Decision**: 僅修改 `ui/` 與必要的 `viewmodels/` 顯示欄位映射，不調整 service/repository/integration 的資料流程。

**Rationale**:
- 規格範圍限定色彩、色調、排版。
- 憲法要求 UI 不可直接觸碰外部 I/O；本次無需更動資料供應商路徑。
- 降低回歸風險，保持 MVP 功能穩定。

**Alternatives considered**:
- 同步調整資料格式與 UI：超出需求範圍，增加不必要風險。

## Implementation Notes (for planning handoff)

- 主要調整目標檔案：
  - `src/midas/ui/theme.py`
  - `src/midas/ui/app_window.py`
  - `src/midas/ui/pages/*.py`
  - `src/midas/ui/components/*.py`
- 驗收需覆蓋頁面：首頁、個股詳情、自選股、設定、資源監控。
- 驗收需覆蓋模式：dark + light。

## Final Implementation Notes (Post-implementation)

- 主題角色已擴充互動 token：`interactive_hover`, `interactive_focus`, `interactive_disabled`。
- spacing token 實作已固定為：`spacing_s=8`, `spacing_m=12`, `spacing_l=20`, `container_padding=20`。
- Provider Boundary Gate 以 `scripts/check_ui_boundary.py` 驗證，UI 層避免 requests/sqlite/FinMind SDK 直連。
- WCAG AA 抽查由 `scripts/check_ui_contrast.py` 執行 sample pair 驗證。
