"""Network information provider service."""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path

from src.domain.models import NetworkInfo


class NetworkService:
    """Collect connection type, SSID, and IP address.

    Works cross-platform: macOS for development, Linux/Raspberry Pi for
    production.  Degrades gracefully when data is unavailable.
    """

    def get_current(self) -> NetworkInfo:
        interfaces = self._active_interfaces()
        connection_type = self._classify(interfaces)
        ip_address = self._local_ip()
        ssid = self._wifi_ssid() if connection_type == "wifi" else None
        online = self._has_default_route()

        return NetworkInfo(
            connection_type=connection_type,
            ssid=ssid,
            ip_address=ip_address,
            online=online,
        )

    @staticmethod
    def _active_interfaces() -> list[str]:
        network_root = Path("/sys/class/net")
        if network_root.exists():
            result: list[str] = []
            for path in network_root.iterdir():
                if path.name == "lo":
                    continue
                try:
                    state = (path / "operstate").read_text(encoding="utf-8").strip()
                except OSError:
                    continue
                if state == "up":
                    result.append(path.name)
            return result
        return [name for _, name in socket.if_nameindex() if name != "lo0"]

    @staticmethod
    def _classify(interfaces: list[str]) -> str:
        for name in interfaces:
            if name.startswith(("eth", "en")):
                return "ethernet"
        for name in interfaces:
            if name.startswith(("wlan", "wl")):
                return "wifi"
        return "unknown"

    @staticmethod
    def _local_ip() -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except OSError:
            return "0.0.0.0"

    @staticmethod
    def _wifi_ssid() -> str | None:
        try:
            result = subprocess.run(
                ["iwgetid", "-r"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return None

    @staticmethod
    def _has_default_route() -> bool:
        try:
            with socket.create_connection(("1.1.1.1", 53), timeout=0.25):
                return True
        except OSError:
            return False
