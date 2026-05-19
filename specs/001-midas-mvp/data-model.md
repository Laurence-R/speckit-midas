# Data Model: Midas MVP

**Phase**: 1 — Design
**Date**: 2026-05-19
**Feature**: [spec.md](spec.md) | [research.md](research.md)

## SQLite Schema

資料庫路徑：`%APPDATA%\Midas\midas.db`  
版本管理：`PRAGMA user_version = 1`（MVP 初始版本）

---

### tracked_stocks — 追蹤股清單

```sql
CREATE TABLE tracked_stocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL UNIQUE,          -- 台股代號 (4–6 碼數字)
    company_name TEXT   NOT NULL,                 -- 公司名稱（由 FinMind TaiwanStockInfo 填入）
    added_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    memo        TEXT    NOT NULL DEFAULT '',      -- 個人備忘 (≤500 字)
    sort_order  INTEGER NOT NULL DEFAULT 0        -- 使用者自訂排序
);
```

**Constraints**:
- `symbol` UNIQUE：不允許重複追蹤同一股票
- `memo` 長度驗證於 Service 層（≤500 字元），DB 不設 CHECK 以保持彈性
- 上限 30 筆由 Service 層 enforce

---

### market_events — 市場事件

```sql
CREATE TABLE market_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol                  TEXT    NOT NULL,
    event_date              TEXT    NOT NULL,   -- YYYY-MM-DD（公告日）
    event_type              TEXT    NOT NULL,   -- 見 EventType enum
    event_type_priority     INTEGER NOT NULL,   -- 1=財報, 2=法說, 3=重訊, 4=一般
    occurred_at             DATETIME NOT NULL,  -- 事件原始發生時間
    title                   TEXT    NOT NULL,   -- 公告標題
    source_url              TEXT    NOT NULL,   -- 原始來源 URL（必填，不可空）
    source_name             TEXT    NOT NULL,   -- 資料來源名稱 e.g. '公開資訊觀測站'
    ai_summary              TEXT,               -- 100–200 字摘要（可 NULL，代表尚未生成）
    ai_summary_generated_at DATETIME,           -- LLM 生成時間
    ai_model                TEXT,               -- e.g. 'gemini-2.5-flash-lite'
    sentiment               TEXT,               -- 'positive'|'neutral'|'negative'|NULL
    disclaimer              TEXT    NOT NULL DEFAULT '此為 AI 摘要，僅供參考，不構成投資建議。',
    fetched_at              DATETIME NOT NULL,  -- 本機抓取時間（可溯源）

    UNIQUE(symbol, event_date, source_url)      -- 防止重複匯入同一事件
);

CREATE INDEX idx_market_events_symbol_date ON market_events(symbol, event_date);
CREATE INDEX idx_market_events_date_priority ON market_events(event_date, event_type_priority);
```

**EventType enum** (儲存為字串):
| value | 顯示標籤 | priority |
|-------|---------|---------|
| `financial_report` | 財報 | 1 |
| `investor_conference` | 法說會 | 2 |
| `material_news` | 重大訊息 | 3 |
| `general_announcement` | 一般公告 | 4 |

**Sentiment enum**: `positive` / `neutral` / `negative` / `NULL`（生成失敗時）

---

### financial_metrics — 財務指標

```sql
CREATE TABLE financial_metrics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT    NOT NULL,
    metric_type  TEXT    NOT NULL,  -- 見 MetricType enum
    period       TEXT    NOT NULL,  -- 'YYYY-QN' e.g. '2025-Q4'
    value        REAL,              -- NULL 表示尚未揭露
    is_unreported INTEGER NOT NULL DEFAULT 0,  -- 1 = 尚未揭露（顯示「尚未揭露」）
    direction    TEXT,              -- 'improving'|'stable'|'declining'|NULL
    change_pct   REAL,              -- 與前一季比較的變化率（%），NULL 表示無前期資料
    source_name  TEXT    NOT NULL,  -- e.g. 'FinMind'
    fetched_at   DATETIME NOT NULL,

    UNIQUE(symbol, metric_type, period)
);

CREATE INDEX idx_financial_metrics_symbol ON financial_metrics(symbol, metric_type, period);
```

**MetricType enum**:
| value | 中文名稱 | 單位 | 計算來源 |
|-------|---------|------|---------|
| `EPS` | 每股盈餘 | 元 | TaiwanStockFinancialStatements（直接取值） |
| `gross_margin` | 毛利率 | % | GrossProfit / (GP + COGS) × 100 |
| `ROE` | 股東權益報酬率 | % | IncomeAfterTaxes / Equity × 100 |
| `debt_ratio` | 負債比率 | % | TotalLiabilities / TotalAssets × 100 |
| `FCF` | 自由現金流 | 百萬元 | OperatingCF − CapEx |

**Direction 判定規則**（`change_pct` 計算完成後套用）:
```
change_pct = (current_value - prev_value) / abs(prev_value) * 100

if change_pct > +5.0  → direction = 'improving'
if change_pct < -5.0  → direction = 'declining'
otherwise             → direction = 'stable'
```

---

### market_overviews — 大盤概況快照

```sql
CREATE TABLE market_overviews (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    trading_date     TEXT    NOT NULL UNIQUE,  -- YYYY-MM-DD
    taiex_close      REAL    NOT NULL,         -- 加權指數收盤點位
    taiex_change     REAL    NOT NULL,         -- 漲跌點數（正/負）
    taiex_change_pct REAL    NOT NULL,         -- 漲跌幅（%）
    volume_b         REAL    NOT NULL,         -- 成交量（億元）
    volume_5d_avg_b  REAL,                     -- 五日均量（億元），可 NULL
    sector_rankings  TEXT    NOT NULL,         -- JSON: [{rank, name, change_pct, direction}]
    institutional    TEXT    NOT NULL,         -- JSON: {foreign_net_b, trust_net_b, dealer_net_b}
    source_name      TEXT    NOT NULL,         -- e.g. 'FinMind'
    fetched_at       DATETIME NOT NULL
);
```

---

### update_jobs — 更新任務紀錄

```sql
CREATE TABLE update_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    triggered_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at     DATETIME,
    status           TEXT    NOT NULL DEFAULT 'running',  -- 'running'|'success'|'failed'|'partial'
    total_steps      INTEGER NOT NULL DEFAULT 0,
    completed_steps  INTEGER NOT NULL DEFAULT 0,
    error_message    TEXT,                      -- 失敗原因（供 UI 顯示）
    llm_calls_made   INTEGER NOT NULL DEFAULT 0,
    llm_tokens_used  INTEGER NOT NULL DEFAULT 0  -- 供成本審計
);
```

---

### app_settings — 應用設定

```sql
CREATE TABLE app_settings (
    key        TEXT    PRIMARY KEY,
    value      TEXT    NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 預設值（初始化時插入）:
-- ('theme', 'dark')
-- ('finmind_token', '')
-- ('gemini_api_key', '')
-- ('last_update_date', '')
-- ('llm_daily_calls', '0')      -- 今日已用呼叫數（每日重置）
-- ('llm_daily_date', '')        -- 用於判斷是否需要重置計數
```

---

## Entity Relationships

```
tracked_stocks (symbol) ←──1:N──→ market_events (symbol)
tracked_stocks (symbol) ←──1:N──→ financial_metrics (symbol)
update_jobs            ←──紀錄── 每次盤後更新
market_overviews       ──獨立── 每交易日一筆
app_settings           ──KV 儲存── 全域設定
```

## Cache Invalidation Rules

| 資料表 | 有效期 | 重新抓取條件 |
|-------|-------|------------|
| `market_events` | 當日收盤後至隔日 09:00 | `event_date != today OR fetched_at < today 09:00` |
| `financial_metrics` | 7 天 | `fetched_at < NOW() - 7 days` |
| `market_overviews` | 當日收盤後至隔日 09:00 | `trading_date != today` |
| `app_settings` | 永久 | 使用者手動修改 |

## Python dataclasses (models layer)

```python
# src/midas/models/market_event.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class EventType(str, Enum):
    FINANCIAL_REPORT = "financial_report"
    INVESTOR_CONFERENCE = "investor_conference"
    MATERIAL_NEWS = "material_news"
    GENERAL_ANNOUNCEMENT = "general_announcement"

    @property
    def priority(self) -> int:
        return {self.FINANCIAL_REPORT: 1, self.INVESTOR_CONFERENCE: 2,
                self.MATERIAL_NEWS: 3, self.GENERAL_ANNOUNCEMENT: 4}[self]

    @property
    def display_label(self) -> str:
        return {self.FINANCIAL_REPORT: "財報", self.INVESTOR_CONFERENCE: "法說會",
                self.MATERIAL_NEWS: "重大訊息", self.GENERAL_ANNOUNCEMENT: "一般公告"}[self]

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

@dataclass
class MarketEvent:
    id: Optional[int]
    symbol: str
    event_date: str             # YYYY-MM-DD
    event_type: EventType
    occurred_at: datetime
    title: str
    source_url: str             # MUST NOT be empty
    source_name: str
    fetched_at: datetime
    ai_summary: Optional[str] = None
    ai_summary_generated_at: Optional[datetime] = None
    ai_model: Optional[str] = None
    sentiment: Optional[Sentiment] = None
    disclaimer: str = "此為 AI 摘要，僅供參考，不構成投資建議。"
```
