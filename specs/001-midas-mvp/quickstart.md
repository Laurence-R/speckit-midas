# Quickstart: Midas 開發環境

**Date**: 2026-05-19

## 前置需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 套件管理工具
- Windows 10/11（開發環境，非強制）
- Gemini API Key（可用 Google AI Studio 免費取得）
- FinMind Token（可選，提升 API 限流至 600 req/hr）

## 初始化專案

```powershell
# 複製專案
git clone <repo-url>
cd midas

# 安裝依賴（uv 會自動建立 .venv）
uv sync

# 複製設定範本
copy .env.example .env
# 編輯 .env，填入 GEMINI_API_KEY 與 FINMIND_TOKEN
```

## 設定 .env

```env
GEMINI_API_KEY=your_gemini_key_here
FINMIND_TOKEN=your_finmind_token_here   # 留空使用免費匿名存取
MIDAS_DATA_DIR=                          # 留空使用預設 %APPDATA%\Midas
MIDAS_ENV=development                    # development | production
```

## 執行應用程式

```powershell
# 開發模式（顯示 console log）
uv run python main.py

# 或直接
.venv\Scripts\python.exe main.py
```

## 執行測試

```powershell
# 所有測試（unit + integration）
uv run pytest

# 僅 unit tests（不需真實 API）
uv run pytest tests/unit/

# 含覆蓋率報告
uv run pytest --cov=src/midas tests/unit/
```

## 開發期間的測試資料

```powershell
# 載入 fixture 資料至本機 SQLite（快速驗證 UI 而不需真實 API）
uv run python scripts/load_fixtures.py

# 清除本機測試資料庫
uv run python scripts/reset_db.py
```

## 專案結構速覽

```
src/midas/
├── app.py          # CTk App + 頁面 Router
├── ui/             # GUI 層（不呼叫外部 API）
├── viewmodels/     # 業務呈現邏輯
├── services/       # 業務邏輯層（含 interfaces.py）
├── agents/         # 資料抓取與 LLM 協作
├── repositories/   # SQLite 存取層
├── models/         # Python dataclasses
├── integrations/   # FinMind / Gemini client
└── tasks/          # Background worker（queue + thread）
```

## 常用指令

| 指令 | 說明 |
|------|------|
| `uv sync` | 安裝 / 同步所有依賴 |
| `uv run pytest tests/unit/` | 跑單元測試（無 API 呼叫） |
| `uv run python main.py` | 開發模式啟動 |
| `uv add <package>` | 新增依賴 |
