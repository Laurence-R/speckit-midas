"""Gemini API client with daily quota management."""
from __future__ import annotations

import logging
import sqlite3
from datetime import date
from typing import Any

from google import genai
from google.genai import types as genai_types

from midas.config import AppConfig
from midas.exceptions import LLMQuotaExceededError

logger = logging.getLogger(__name__)

MODEL = "gemini-3.5-flash"
DAILY_CALL_LIMIT = 50

SYSTEM_PROMPT = (
    "你是一位台股財經研究助理，負責整理新聞摘要並以「長期投資」視角進行分析解讀。\n\n"
    "分析原則：\n"
    "• 區分「短期情緒反應」、「結構性改變」與「一次性事件」，不做短期股價預測\n"
    "• 連結新聞與企業長期競爭力及基本面方向（營收成長率、毛利率、現金流、資本支出）\n"
    "• 無法從公開資料驗證的推論須標示「推測」或「不確定」；嚴禁虛構數字\n"
    "• 嚴格禁止任何買進／賣出／持有等投資建議\n\n"
    "每則事件的 summary 欄位必須依以下固定格式輸出（純文字，不使用 Markdown）：\n\n"
    "【新聞摘要】\n"
    "<2–3 句話概括報導核心事實，說明發生了什麼事、涉及哪家公司或哪個事件>\n\n"
    "【分析解讀】\n"
    "①事件性質：<屬於結構性改變、一次性事件或短期情緒反應，並點出核心事實>\n"
    "②長期基本面：<對營收成長率、毛利率或現金流的方向性影響（上升／下降／不明），區分短期（1 年內）與中長期（1 年以上）效果>\n"
    "③風險：<至少一項，區分「已發生的事實」與「需持續追蹤的潛在風險」>\n\n"
    "sentiment 依企業「長期基本面」而非短期股價情緒判斷：\n"
    "• positive：基本面有具體改善或長期競爭力獲強化\n"
    "• negative：基本面有具體惡化或長期假設被削弱\n"
    "• neutral：屬一次性事件或資訊不足以判斷長期影響\n\n"
    "輸出格式：純 JSON，不加任何 Markdown code block\n"
    '{"events": [{"id": <int>, "summary": <str>, "sentiment": "positive|neutral|negative"}]}'
)


class GeminiClient:
    """Wrapper for the Gemini generative AI API with per-day quota control.

    Daily call tracking is stored in the ``app_settings`` SQLite table so it
    persists across process restarts.
    """

    def __init__(
        self,
        config: AppConfig | None = None,
        db_conn: sqlite3.Connection | None = None,
    ) -> None:
        if config is None:
            from midas.config import load_config
            config = load_config()
        self._db_conn = db_conn  # may be None when testing without DB
        # Build client immediately if key is in env/.env;
        # otherwise defer to _get_client() which reads from DB at call time.
        api_key: str = config.gemini_api_key
        self._genai: genai.Client | None = (
            genai.Client(api_key=api_key) if api_key else None
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, system_prompt: str, user_text: str) -> str:
        """Call Gemini and return the raw text response.

        Raises
        ------
        LLMQuotaExceededError
            When the daily call count has already reached 50 for today.
        """
        self._check_and_increment_quota()
        prompt = f"{system_prompt}\n\n{user_text}"
        try:
            response = self._get_client().models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return response.text
        except Exception as exc:
            # Roll back the quota increment on failure
            self._decrement_quota()
            raise exc from exc

    def get_daily_usage(self) -> tuple[int, int]:
        """Return (calls_made_today, 0) — tokens_used tracking is via UpdateJob."""
        return self._read_quota(), 0

    # ------------------------------------------------------------------
    # Internal: client builder
    # ------------------------------------------------------------------

    def _get_client(self) -> genai.Client:
        """Return the genai.Client, building it lazily from the DB key if needed."""
        if self._genai is not None:
            return self._genai
        # Read API key from app_settings (saved via Settings page)
        api_key = ""
        if self._db_conn is not None:
            row = self._db_conn.execute(
                "SELECT value FROM app_settings WHERE key = 'gemini_api_key'"
            ).fetchone()
            if row:
                api_key = row["value"] or ""
        if not api_key:
            raise ValueError(
                "Gemini API key 未設定，請至「設定」頁面填入 Gemini API Key。"
            )
        self._genai = genai.Client(api_key=api_key)
        return self._genai

    # ------------------------------------------------------------------
    # Quota helpers
    # ------------------------------------------------------------------

    def _check_and_increment_quota(self) -> None:
        today = str(date.today())
        calls, recorded_date = self._read_quota_with_date()
        if recorded_date == today and calls >= DAILY_CALL_LIMIT:
            raise LLMQuotaExceededError(
                f"Daily Gemini call limit ({DAILY_CALL_LIMIT}) reached for {today}."
            )
        # Reset counter if the date has changed
        new_calls = (calls + 1) if recorded_date == today else 1
        self._write_quota(new_calls, today)

    def _decrement_quota(self) -> None:
        today = str(date.today())
        calls, recorded_date = self._read_quota_with_date()
        if recorded_date == today and calls > 0:
            self._write_quota(calls - 1, today)

    def _read_quota(self) -> int:
        calls, _ = self._read_quota_with_date()
        return calls

    def _read_quota_with_date(self) -> tuple[int, str]:
        if self._db_conn is None:
            return 0, ""
        row = self._db_conn.execute(
            "SELECT value FROM app_settings WHERE key = 'llm_daily_calls'"
        ).fetchone()
        calls = int(row["value"]) if row else 0
        row_date = self._db_conn.execute(
            "SELECT value FROM app_settings WHERE key = 'llm_daily_date'"
        ).fetchone()
        daily_date = row_date["value"] if row_date else ""
        return calls, daily_date

    def _write_quota(self, calls: int, date_str: str) -> None:
        if self._db_conn is None:
            return
        self._db_conn.execute(
            "UPDATE app_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = 'llm_daily_calls'",
            (str(calls),),
        )
        self._db_conn.execute(
            "UPDATE app_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = 'llm_daily_date'",
            (date_str,),
        )
        self._db_conn.commit()
