"""InkPi core orchestration service."""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from inkpi.config import default_config_path, load_config
from inkpi.contracts import FrameMetadata
from inkpi.dashboard.controller import DashboardController
from inkpi.dashboard.pages.overview import OverviewPage
from inkpi.display.service import DEFAULT_SOCKET as DISPLAY_SOCKET
from inkpi.display.service import DisplayClient
from inkpi.ipc import serve
from inkpi.management.service import LocalManagementService

DEFAULT_CORE_SOCKET = Path(os.getenv("INKPI_CORE_SOCKET", "/run/inkpi-core/core.sock"))


class InkPiCore:
    """Coordinate dashboard scheduling while serving concurrent control requests."""

    def __init__(
        self,
        controller: DashboardController,
        display: DisplayClient,
        management: LocalManagementService,
        refresh_seconds: int = 60,
    ) -> None:
        self._controller = controller
        self._display = display
        self._management = management
        self._refresh_seconds = max(10, refresh_seconds)
        self._running = False
        self._worker: threading.Thread | None = None
        self._last_display_result: dict[str, Any] | None = None
        self._last_error: str | None = None
        self._logger = logging.getLogger(self.__class__.__name__)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker = threading.Thread(target=self._run, name="inkpi-core-scheduler", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._running = False
        if self._worker:
            self._worker.join(timeout=10)

    def handle_request(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Serve dashboard controls and management facts without blocking on refreshes."""

        if action == "health":
            return {"healthy": self._running, "last_error": self._last_error}
        if action == "get_pages":
            return {"pages": [asdict(page) for page in self._controller.get_pages()]}
        if action == "set_page_enabled":
            return asdict(
                self._controller.set_page_enabled(str(payload["page_id"]), bool(payload["enabled"]))
            )
        if action == "get_dashboard_status":
            return asdict(self._controller.get_status())
        if action == "get_display_status":
            return asdict(self._display.get_status())
        if action == "get_system_status":
            return asdict(self._management.get_system_status())
        if action == "get_network_status":
            return asdict(self._management.get_network_status())
        if action == "get_core_status":
            return {
                "healthy": self._running,
                "last_error": self._last_error,
                "last_display_result": self._last_display_result,
            }
        raise ValueError(f"unknown core action: {action}")

    def _run(self) -> None:
        while self._running:
            started = time.monotonic()
            try:
                page_id, frame = self._controller.render_next()
                result = self._display.submit_frame(frame, FrameMetadata(page_id=page_id))
                self._last_display_result = asdict(result)
                self._last_error = None if result.accepted else result.reason
            except Exception as error:
                self._last_error = str(error)
                self._logger.exception("core_refresh_cycle_failed")
            remaining = self._refresh_seconds - (time.monotonic() - started)
            self._sleep(max(0, remaining))

    def _sleep(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while self._running and time.monotonic() < deadline:
            time.sleep(min(0.2, deadline - time.monotonic()))


def build_core(
    *,
    config_path: str | None = None,
    display_socket: str | Path = DISPLAY_SOCKET,
) -> InkPiCore:
    """Build the production core composition root."""

    path = config_path or str(default_config_path())
    config = load_config(path)
    management = LocalManagementService()
    controller = DashboardController(
        [OverviewPage(management)],
        config,
        config_path=path,
    )
    return InkPiCore(
        controller,
        DisplayClient(display_socket),
        management,
        refresh_seconds=int(os.getenv("INKPI_REFRESH_SECONDS", "15")),
    )


def run_core_service(
    socket_path: str | Path = DEFAULT_CORE_SOCKET,
    *,
    config_path: str | None = None,
    display_socket: str | Path = DISPLAY_SOCKET,
) -> None:
    """Run core scheduling and its local control API."""

    core = build_core(config_path=config_path, display_socket=display_socket)
    core.start()
    try:
        serve(socket_path, core.handle_request)
    finally:
        core.stop()
