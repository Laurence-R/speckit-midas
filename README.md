# Midas

Midas 是一套台股盤後投研桌面應用，使用 Python 3.12 與 CustomTkinter 建置，採本機 SQLite 儲存，並整合 FinMind 與 Gemini。

## 1. 系統介紹

- 目標平台：Windows 10/11
- 執行型態：桌面 GUI
- 本機資料庫：SQLite（啟動時自動初始化）
- 主要資料來源：FinMind
- AI 摘要模型：gemini-3.5-flash
- 已實作頁面：首頁、自選股、個股詳情、資源監控、設定

## 2. 目標使用者

- 需要在盤後快速瀏覽台股重點事件與大盤概況的投資人
- 想維護自選股名單，並持續追蹤新聞與財務指標的使用者
- 需要在單機環境保存資料，不依賴雲端資料庫的使用者

## 3. 安裝與執行步驟

1. 取得專案

```powershell
git clone https://github.com/Laurence-R/speckit-midas
cd midas
```

2. 安裝 uv（若尚未安裝）

- 官方文件：https://docs.astral.sh/uv/

3. 安裝相依套件

```powershell
uv sync --dev
```

4. 啟動應用

```powershell
uv run main.py
```

5. 在設定頁輸入金鑰（主要流程）

- 進入「設定」頁
- 輸入並儲存 FinMind Token
- 輸入並儲存 Gemini API Key

6. 基本使用

- 到「自選股」頁新增股票代號
- 在「首頁」或「個股詳情」查看事件與財務
- 在「資源監控」查看 FinMind 用量與本機快取狀態

7. 可選：使用 `.env` 預先帶入金鑰（進階）

若你希望在啟動時自動帶入金鑰，可建立 `.env`：

```powershell
copy .env.example .env
```

編輯 `.env`：

```env
GEMINI_API_KEY=your_gemini_key_here
FINMIND_TOKEN=your_finmind_token_here
MIDAS_DATA_DIR=
MIDAS_ENV=development
```

說明：

- `.env` 不是必要條件
- 系統主要流程是由使用者在「設定」頁輸入並儲存金鑰
- 若 `.env` 有值，啟動時會同步到本機設定（僅在本機設定為空值時）

## 4. 架構

分層架構：

- UI：`src/midas/ui`
- ViewModel：`src/midas/viewmodels`
- Service：`src/midas/services`
- Agent：`src/midas/agents`
- Repository：`src/midas/repositories`
- Integration：`src/midas/integrations`

依賴方向：

- UI -> ViewModel -> Service -> Repository -> SQLite
- Agent -> Integration -> External APIs

資料來源實作（目前程式碼已串接）：

- FinMind DataLoader + TaiwanStockNews REST API
- Google GenAI SDK（gemini-3.5-flash）

## 5. 免責聲明

本系統中的 AI 摘要僅供參考，不構成任何投資建議。請使用者自行判斷並承擔投資風險。