# Quickstart: Modernize SaaS UI Tone and Layout

**Date**: 2026-05-23  
**Feature**: [spec.md](spec.md)

本文件提供本功能的最小實作與驗收流程，聚焦 UI 主題與排版，不涉及資料流程變更。

## 1. 前置條件

- 已完成 `uv sync`。
- 可正常啟動 Midas：`uv run python main.py`。
- 目前分支為 `003-modernize-saas-ui`。

## 2. 建議修改範圍

- `src/midas/ui/theme.py`
- `src/midas/ui/app_window.py`
- `src/midas/ui/pages/*.py`
- `src/midas/ui/components/*.py`

禁止擴散到：
- `src/midas/services/`
- `src/midas/repositories/`
- `src/midas/integrations/`

## 3. 實作步驟

1. 在 `theme.py` 定義雙模式語意色彩角色（dark + light）。
2. 定義 spacing token 級距（S/M/L）並建立共用存取方式。
3. 套用到主要頁面與共用元件，移除零散 magic spacing。
4. 補齊互動狀態（default/hover/focus/disabled）與語意狀態色映射。
5. 檢查頁面在中高密度策略下無過多留白且不擁擠。

## 4. 驗收流程

### 4.1 啟動與手動檢查

```powershell
uv run python main.py
```

逐頁檢查：
- Dashboard
- Stock Detail
- Watchlist
- Settings
- Resource Monitor

每頁都檢查 dark/light 切換後：
- 色彩語言是否一致
- 留白是否符合中高密度
- 狀態色是否可辨識

### 4.2 對比檢查

- 一般文字對比 >= 4.5:1
- 大字對比 >= 3:1

至少抽查：
- 導航標題
- 主要卡片標題與內容文字
- 按鈕文字
- 狀態列訊息

### 4.3 留白 token 檢查

- 以 S/M/L token 驗證目標頁面區塊間距。
- 目標：至少 95% 區塊符合 token 規則。

## 5. 測試指令

先執行 Gate 驗證腳本：

```powershell
uv run python scripts/check_ui_boundary.py
uv run python scripts/check_ui_contrast.py
uv run python scripts/check_spacing_tokens.py
```

```powershell
uv run pytest tests/unit/
```

若有 UI 相關測試，建議加跑：

```powershell
uv run pytest tests/unit/test_resource_monitor_page.py
```

## 6. 完成定義 (DoD)

- 深色與亮色模式同步完成。
- WCAG AA 對比基準達標。
- spacing token 驗收達標。
- 不改動資料流程與架構邊界。
- 主要任務操作可用性無顯著退化。

## 7. 驗收證據檔

- `specs/003-modernize-saas-ui/checklists/theme-audit.md`
- `specs/003-modernize-saas-ui/checklists/ux-scoring-results.md`
- `specs/003-modernize-saas-ui/checklists/completion-rate-comparison.md`