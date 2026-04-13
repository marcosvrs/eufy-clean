"""Global fixtures for robovac_mqtt integration tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True, scope="session")
def allow_pycares_shutdown_thread() -> Generator[None]:
    """Rename pycares shutdown thread so HA cleanup ignores it.

    pycares 4.11 starts a daemon thread named ``_run_safe_shutdown_loop`` the first
    time a channel is destroyed. That thread is process-global and intentionally
    long-lived, so pytest-homeassistant-custom-component treats it as a lingering
    foreign thread unless it uses an allowed prefix.
    """

    try:
        import pycares
    except ImportError:
        yield
        return

    original_start = pycares._shutdown_manager.start

    def _patched_start() -> None:
        original_start()
        thread = pycares._shutdown_manager._thread
        if thread is not None and "_run_safe_shutdown_loop" in thread.name:
            thread.name = "waitpid-pycares-shutdown"

    with patch.object(pycares._shutdown_manager, "start", side_effect=_patched_start):
        yield


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations,
) -> Generator[None]:
    """Enable custom integrations defined in the test dir."""
    yield
