"""Unit tests for Orchestrator 4-step pipeline."""
from __future__ import annotations

import queue
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from midas.agents.orchestrator import Orchestrator, _TOTAL_STEPS
from midas.models.market_event import EventType, MarketEvent
from midas.models.market_overview import MarketOverview
from midas.models.update_job import JobStatus, UpdateJob


def _make_event(symbol: str = "2330") -> MarketEvent:
    return MarketEvent(
        symbol=symbol,
        event_date="2025-01-01",
        event_type=EventType.FINANCIAL_REPORT,
        occurred_at=datetime(2025, 1, 1, 10, 0),
        title="Test Event",
        source_url="https://example.com",
        source_name="FinMind",
        fetched_at=datetime(2025, 1, 1, 10, 0),
    )


def _make_overview() -> MarketOverview:
    return MarketOverview(
        trading_date="2025-01-01",
        taiex_close=21000.0,
        taiex_change=100.0,
        taiex_change_pct=0.48,
        volume_b=2500.0,
        sector_rankings=[],
        institutional={},
        source_name="FinMind",
        fetched_at=datetime(2025, 1, 1, 10, 0),
    )


@pytest.fixture()
def q() -> queue.Queue:
    return queue.Queue()


@pytest.fixture()
def mock_market_agent() -> MagicMock:
    agent = MagicMock()
    agent.fetch_overview.return_value = _make_overview()
    return agent


@pytest.fixture()
def mock_announcement_agent() -> MagicMock:
    agent = MagicMock()
    agent.fetch_announcements.return_value = [_make_event()]
    return agent


@pytest.fixture()
def mock_financial_agent() -> MagicMock:
    agent = MagicMock()
    agent.fetch_and_calculate.return_value = []
    return agent


@pytest.fixture()
def mock_job_repo() -> MagicMock:
    repo = MagicMock()
    repo.create.return_value = 1
    return repo


@pytest.fixture()
def mock_app_setting_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_metric_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def orchestrator(
    q, mock_market_agent, mock_announcement_agent,
    mock_financial_agent, mock_job_repo, mock_metric_repo, mock_app_setting_repo,
) -> Orchestrator:
    return Orchestrator(
        market_agent=mock_market_agent,
        announcement_agent=mock_announcement_agent,
        financial_agent=mock_financial_agent,
        market_overview_repo=MagicMock(),
        market_event_repo=MagicMock(),
        financial_metric_repo=mock_metric_repo,
        update_job_repo=mock_job_repo,
        app_setting_repo=mock_app_setting_repo,
        result_queue=q,
    )


class TestOrchestratorHappyPath:
    def test_all_steps_emit_progress(self, orchestrator: Orchestrator, q: queue.Queue) -> None:
        orchestrator.run(["2330"])
        messages = []
        while not q.empty():
            messages.append(q.get_nowait())
        progress = [m for m in messages if m[0] == "progress"]
        assert len(progress) == _TOTAL_STEPS

    def test_progress_steps_are_sequential(self, orchestrator: Orchestrator, q: queue.Queue) -> None:
        orchestrator.run(["2330"])
        steps = []
        while not q.empty():
            msg = q.get_nowait()
            if msg[0] == "progress":
                steps.append(msg[1]["step"])
        assert steps == list(range(1, _TOTAL_STEPS + 1))

    def test_emits_update_complete_on_success(self, orchestrator: Orchestrator, q: queue.Queue) -> None:
        orchestrator.run(["2330"])
        messages = []
        while not q.empty():
            messages.append(q.get_nowait())
        events = [m for m in messages if m[0] == "update_complete"]
        assert len(events) == 1
        assert events[0][1].status == JobStatus.SUCCESS

    def test_job_repo_create_and_complete_called(
        self, orchestrator: Orchestrator, mock_job_repo: MagicMock, q: queue.Queue
    ) -> None:
        orchestrator.run(["2330"])
        mock_job_repo.create.assert_called_once()
        mock_job_repo.complete.assert_called_once()

    def test_persists_last_update_date(
        self,
        orchestrator: Orchestrator,
        mock_app_setting_repo: MagicMock,
    ) -> None:
        orchestrator.run(["2330"], target_date="2026-05-22")
        mock_app_setting_repo.set_value.assert_called_once_with("last_update_date", "2026-05-22")

    def test_no_update_error_on_success(self, orchestrator: Orchestrator, q: queue.Queue) -> None:
        orchestrator.run(["2330"])
        messages = []
        while not q.empty():
            messages.append(q.get_nowait())
        errors = [m for m in messages if m[0] == "update_error"]
        assert errors == []


class TestOrchestratorStep2Failure:
    def test_step2_failure_does_not_halt_pipeline(
        self,
        orchestrator: Orchestrator,
        mock_announcement_agent: MagicMock,
        q: queue.Queue,
    ) -> None:
        """Individual symbol failures in Step 2 should not crash the pipeline."""
        mock_announcement_agent.fetch_announcements.side_effect = RuntimeError("network error")
        orchestrator.run(["2330"])
        messages = []
        while not q.empty():
            messages.append(q.get_nowait())
        complete = [m for m in messages if m[0] == "update_complete"]
        assert len(complete) == 1  # pipeline should still complete


class TestOrchestratorStep1CriticalFailure:
    def test_step1_failure_emits_update_error(
        self,
        orchestrator: Orchestrator,
        mock_market_agent: MagicMock,
        mock_job_repo: MagicMock,
        q: queue.Queue,
    ) -> None:
        mock_market_agent.fetch_overview.side_effect = RuntimeError("API down")
        orchestrator.run(["2330"])
        messages = []
        while not q.empty():
            messages.append(q.get_nowait())
        errors = [m for m in messages if m[0] == "update_error"]
        assert len(errors) == 1
        mock_job_repo.fail.assert_called_once()

    def test_step1_failure_job_status_failed(
        self,
        orchestrator: Orchestrator,
        mock_market_agent: MagicMock,
        q: queue.Queue,
    ) -> None:
        mock_market_agent.fetch_overview.side_effect = RuntimeError("API down")
        orchestrator.run(["2330"])
        messages = []
        while not q.empty():
            messages.append(q.get_nowait())
        complete = [m for m in messages if m[0] == "update_complete"]
        assert complete == []  # no success signal
