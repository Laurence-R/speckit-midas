from __future__ import annotations

from unittest.mock import MagicMock

from midas.ui.pages.resource_monitor_page import _get_finmind_usage_state


def test_get_finmind_usage_state_defaults_when_client_missing() -> None:
    assert _get_finmind_usage_state(None) == (False, 0, 600)


def test_get_finmind_usage_state_reads_client_values() -> None:
    client = MagicMock()
    client.has_token.return_value = True
    client.get_api_usage.return_value = (120, 600)

    assert _get_finmind_usage_state(client) == (True, 120, 600)