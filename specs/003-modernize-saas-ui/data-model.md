# Data Model: Modernize SaaS UI Tone and Layout

**Phase**: 1 - Design  
**Date**: 2026-05-23  
**Feature**: [spec.md](spec.md) | [research.md](research.md)

本次功能僅涉及 UI 視覺層，不新增 SQLite 實體與資料表；以下為「設計資料模型」與驗收所需的結構化定義。

## 1. ThemePalette

**Purpose**: 定義雙主題的語意化色彩角色。

**Fields**:
- `mode`: `dark | light`
- `bg_primary`: 頁面主背景
- `bg_secondary`: 區塊背景
- `bg_card`: 卡片背景
- `text_primary`: 主要文字
- `text_secondary`: 次要文字
- `accent`: 主要強調色
- `border`: 邊框/分隔線
- `success`: 正向狀態色
- `warning`: 警示狀態色
- `error`: 錯誤狀態色
- `sentiment_positive`: 正向情緒色（台股慣例）
- `sentiment_negative`: 負向情緒色（台股慣例）
- `sentiment_neutral`: 中性情緒色

**Validation rules**:
- 每個 `mode` 必須完整定義上述角色。
- `text_primary` / `text_secondary` 對各自背景需符合 WCAG AA。

## 2. SpacingTokenSet

**Purpose**: 控制全站留白與排版密度，作為跨頁一致驗收依據。

**Fields**:
- `spacing_s`: 緊湊間距（元件內部、相鄰控制項）
- `spacing_m`: 標準間距（卡片內容、行區塊）
- `spacing_l`: 區塊間距（卡片與卡片、頁面分段）
- `container_padding`: 主內容區邊界留白

**Validation rules**:
- 同類型元件在不同頁面須套用相同級距規則。
- 不允許頁面自行定義未註冊的間距值（避免失控留白）。
- 目標頁面至少 95% 區塊符合 token 規則（對應 SC-008）。

## 3. ComponentStyleProfile

**Purpose**: 定義互動元件在不同狀態的風格映射。

**Fields**:
- `component_type`: `button | entry | label | textbox | card | badge`
- `state`: `default | hover | focus | disabled`
- `bg_role`: 參照 `ThemePalette` 的背景角色
- `fg_role`: 參照 `ThemePalette` 的文字/前景角色
- `border_role`: 參照 `ThemePalette` 的邊框角色

**Validation rules**:
- 所有互動元件必須包含四種狀態。
- `focus` 狀態需可被明確辨識，不可與 `default` 混淆。

## 4. StatusSemanticStyle

**Purpose**: 定義狀態語意顯示的一致規則。

**Fields**:
- `semantic_type`: `positive | warning | negative | neutral`
- `color_role`: 參照 `ThemePalette`
- `text_emphasis`: `normal | strong`
- `applies_to`: `status_bar | card_badge | inline_message`

**Validation rules**:
- 同一語意在全頁面使用同一套色彩角色。
- 不同語意之間需具可辨識差異，不可互相衝突。

## 5. ThemeAuditRecord (Design-time)

**Purpose**: 記錄本次視覺驗收結果（非業務資料，不需入庫）。

**Fields**:
- `page_name`
- `mode`: `dark | light`
- `contrast_pass_rate`
- `spacing_token_pass_rate`
- `consistency_issues`
- `reviewer`
- `reviewed_at`

**State transitions**:
- `draft` -> `reviewed` -> `accepted`
- 若檢查未通過：`reviewed` -> `rework` -> `reviewed`

## Relationships

- `ThemePalette` 1:N `ComponentStyleProfile`
- `SpacingTokenSet` 1:N `ComponentStyleProfile`
- `ThemePalette` 1:N `StatusSemanticStyle`
- `ThemeAuditRecord` 針對每個 `page_name x mode` 形成一筆驗收記錄

## Out of Scope Data Changes

- 不新增或修改 SQLite schema。
- 不修改 `services/`, `repositories/`, `integrations/` 的資料欄位與流程。
- 不新增外部 API 契約。