"""Read-only management facts used by dashboard pages and future admin UI."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

from inkpi.contracts import NetworkStatus, SystemStatus
from src.services.system import SystemService


class LocalManagementService:
    """Collect system and network state without performing privileged changes."""

    def __init__(self) -> None:
        self._system = SystemService()
        self._system_lock = threading.Lock()

    def get_system_status(self) -> SystemStatus:
        with self._system_lock:
            raw = self._system.get_current()
        return SystemStatus(
            uptime_seconds=self._uptime_seconds(),
            cpu_average_percent=raw.cpu_average_percent,
            cpu_peak_percent=raw.cpu_peak_percent,
            memory_used_gb=raw.memory_used_gb,
            memory_total_gb=raw.memory_total_gb,
            memory_percent=raw.memory_percent,
        )

    def get_network_status(self) -> NetworkStatus:
        network_root = Path("/sys/class/net")
        if network_root.exists():
            interfaces = [
                path.name
                for path in network_root.iterdir()
                if path.name != "lo" and self._is_interface_up(path)
            ]
        else:
            interfaces = [name for _, name in socket.if_nameindex() if name != "lo0"]
        return NetworkStatus(
            online=self._has_default_route(),
            ethernet_connected=any(name.startswith(("eth", "en")) for name in interfaces),
            wifi_connected=any(name.startswith(("wlan", "wl")) for name in interfaces),
            active_interfaces=interfaces,
        )

    @staticmethod
    def _uptime_seconds() -> float:
        uptime = Path("/proc/uptime")
        if uptime.exists():
            return float(uptime.read_text(encoding="utf-8").split()[0])
        return time.monotonic()

    @staticmethod
    def _is_interface_up(path: Path) -> bool:
        try:
            return (path / "operstate").read_text(encoding="utf-8").strip() == "up"
        except OSError:
            return False

    @staticmethod
    def _has_default_route() -> bool:
        try:
            with socket.create_connection(("1.1.1.1", 53), timeout=0.25):
                return True
        except OSError:
            return False
