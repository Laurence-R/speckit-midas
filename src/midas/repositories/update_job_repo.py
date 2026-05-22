"""UpdateJob repository implementation."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from midas.models.update_job import JobStatus, UpdateJob
from midas.repositories.interfaces import IUpdateJobRepository


class UpdateJobRepo(IUpdateJobRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # IUpdateJobRepository
    # ------------------------------------------------------------------

    def create(self, job: UpdateJob) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO update_jobs
                (triggered_at, status, total_steps, completed_steps,
                 llm_calls_made, llm_tokens_used)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job.triggered_at.isoformat(),
                job.status.value,
                job.total_steps,
                job.completed_steps,
                job.llm_calls_made,
                job.llm_tokens_used,
            ),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def update_progress(
        self,
        job_id: int,
        completed_steps: int,
        total_steps: int,
        label: str = "",
    ) -> None:
        self._conn.execute(
            """
            UPDATE update_jobs
               SET completed_steps = ?, total_steps = ?
             WHERE id = ?
            """,
            (completed_steps, total_steps, job_id),
        )
        self._conn.commit()

    def complete(
        self, job_id: int, llm_calls: int = 0, llm_tokens: int = 0
    ) -> None:
        self._conn.execute(
            """
            UPDATE update_jobs
               SET status = ?, completed_at = ?,
                   llm_calls_made = ?, llm_tokens_used = ?
             WHERE id = ?
            """,
            (
                JobStatus.SUCCESS.value,
                datetime.now().isoformat(),
                llm_calls,
                llm_tokens,
                job_id,
            ),
        )
        self._conn.commit()

    def fail(self, job_id: int, error_msg: str) -> None:
        self._conn.execute(
            """
            UPDATE update_jobs
               SET status = ?, completed_at = ?, error_message = ?
             WHERE id = ?
            """,
            (
                JobStatus.FAILED.value,
                datetime.now().isoformat(),
                error_msg,
                job_id,
            ),
        )
        self._conn.commit()

    def get_latest(self) -> UpdateJob | None:
        row = self._conn.execute(
            "SELECT * FROM update_jobs ORDER BY triggered_at DESC LIMIT 1"
        ).fetchone()
        return self._row_to_model(row) if row else None

    def get_latest_success(self) -> UpdateJob | None:
        row = self._conn.execute(
            """
            SELECT * FROM update_jobs
            WHERE status = ?
            ORDER BY completed_at DESC, triggered_at DESC, id DESC
            LIMIT 1
            """,
            (JobStatus.SUCCESS.value,),
        ).fetchone()
        return self._row_to_model(row) if row else None

    def get_history(self, limit: int = 20) -> list[UpdateJob]:
        rows = self._conn.execute(
            "SELECT * FROM update_jobs ORDER BY triggered_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> UpdateJob:
        return UpdateJob(
            id=row["id"],
            triggered_at=datetime.fromisoformat(row["triggered_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
            status=JobStatus(row["status"]),
            total_steps=row["total_steps"],
            completed_steps=row["completed_steps"],
            error_message=row["error_message"],
            llm_calls_made=row["llm_calls_made"],
            llm_tokens_used=row["llm_tokens_used"],
        )
