"""UpdateJob dataclass and JobStatus enum."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class UpdateJob:
    status: JobStatus = JobStatus.RUNNING
    total_steps: int = 0
    completed_steps: int = 0
    llm_calls_made: int = 0
    llm_tokens_used: int = 0
    triggered_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    error_message: str | None = None
    id: int | None = None
