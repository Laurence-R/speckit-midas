# Contract: UI Theme and Layout Consistency

**Feature**: [../spec.md](../spec.md)  
**Phase**: 1 - Design

此契約定義本次改版在 UI 層的可驗收邊界，供 pages/components/viewmodels 實作與 code review 使用。

## 1. Scope Contract

- 允許調整：主題色彩、色調、排版密度與留白。
- 禁止調整：業務流程、資料抓取流程、Repository/Service 邏輯。
- UI 層不得新增直連外部 I/O（FinMind SDK / requests / sqlite driver）。

## 2. Theme Mode Contract

- 必須同時支援 `dark` 與 `light` 兩種模式。
- 兩種模式須具備一致的語意角色集合：
  - `bg_primary`, `bg_secondary`, `bg_card`
  - `text_primary`, `text_secondary`
  - `accent`, `border`
  - `success`, `warning`, `error`
  - `sentiment_positive`, `sentiment_negative`, `sentiment_neutral`
  - `interactive_hover`, `interactive_focus`, `interactive_disabled`
- 任一頁面不得只在單一模式完成視覺調整。

## 3. Accessibility Contract

- 一般文字對背景對比 >= 4.5:1。
- 較大文字對背景對比 >= 3:1。
- 對比驗收需覆蓋 dark/light 兩模式的主要頁面與共用元件。

## 4. Spacing Contract

- 必須定義 spacing token 級距：`spacing_s`, `spacing_m`, `spacing_l`, `container_padding`。
- 頁面區塊間距、卡片內距、列表垂直節奏需使用 token，不得任意散佈 magic number。
- 目標頁面至少 95% 區塊符合 token 級距規範。

## 5. Component State Contract

- 互動元件狀態必須完整：`default`, `hover`, `focus`, `disabled`。
- 狀態色彩與邊框行為須可辨識且跨頁一致。
- 狀態語意標示（正向/警示/負向/中性）需固定映射，不可每頁自定義。

## 6. Verification Contract

最低驗收項目：
- 首頁、個股詳情、自選股、設定、資源監控五頁皆通過。
- dark/light 兩模式皆通過。
- 對比與留白 token 驗收結果可追溯（檢查清單或測試紀錄）。

## 7. Non-Goals

- 不新增 API contract。
- 不修改 DB schema。
- 不變更功能導航或資料更新行為。