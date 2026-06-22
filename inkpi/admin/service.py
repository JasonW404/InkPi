"""Read-only admin portal composition."""

from __future__ import annotations

import socket
from dataclasses import asdict, dataclass
from typing import Protocol

from inkpi.admin.events import AdminEventLog
from inkpi.admin.network_policy import NetworkPolicyDecision, NetworkPolicyInput
from inkpi.admin.network_policy import decide_network_access_policy
from inkpi.admin.operations import InMemoryNetworkHelper, NetworkHelper, NetworkOperationAction
from inkpi.admin.operations import build_operation_request
from inkpi.admin.portal import ADMIN_SECTIONS
from inkpi.contracts import (
    DashboardConfigResult,
    DashboardStatus,
    DisplayStatus,
    NetworkStatus,
    PageStatus,
    SystemStatus,
)


class AdminCoreClient(Protocol):
    """Core client surface consumed by the admin portal."""

    def get_system_status(self) -> SystemStatus: ...

    def get_network_status(self) -> NetworkStatus: ...

    def get_status(self) -> DashboardStatus: ...

    def get_pages(self) -> list[PageStatus]: ...

    def get_display_status(self) -> DisplayStatus: ...

    def get_core_status(self) -> dict: ...

    def set_page_enabled(self, page_id: str, enabled: bool) -> DashboardConfigResult: ...


@dataclass(frozen=True)
class AdminSnapshot:
    """Single read model used by admin HTML and JSON routes."""

    hostname: str
    sections: list[dict]
    system: dict
    network: dict
    dashboard: dict
    pages: list[dict]
    display: dict
    core: dict
    network_policy: dict
    summary: dict


class AdminService:
    """Compose read-only admin state from core contracts."""

    def __init__(
        self,
        client: AdminCoreClient,
        network_helper: NetworkHelper | None = None,
        event_log: AdminEventLog | None = None,
    ) -> None:
        self._client = client
        self._network_helper = network_helper or InMemoryNetworkHelper()
        self._events = event_log or AdminEventLog()

    def snapshot(self) -> AdminSnapshot:
        system = self._client.get_system_status()
        network = self._client.get_network_status()
        dashboard = self._client.get_status()
        pages = self._client.get_pages()
        display = self._client.get_display_status()
        core = self._client.get_core_status()
        policy = decide_network_access_policy(_policy_input_from_network(network))

        return AdminSnapshot(
            hostname=socket.gethostname(),
            sections=[asdict(section) for section in ADMIN_SECTIONS],
            system=asdict(system),
            network=asdict(network),
            dashboard=_dashboard_payload(dashboard),
            pages=[asdict(page) for page in pages],
            display=asdict(display),
            core=core,
            network_policy=asdict(policy),
            summary=_summary(network, display, core, policy),
        )

    def status_payload(self) -> dict:
        return asdict(self.snapshot())

    def submit_network_operation(
        self,
        action: NetworkOperationAction,
        payload: dict[str, object] | None = None,
    ) -> dict:
        request = build_operation_request(action, payload or {})
        operation = self._network_helper.submit(request).to_payload()
        self._events.record(
            source="network",
            message=str(operation["message"]),
            details={
                "action": operation["action"],
                "operation_id": operation["operation_id"],
                "request": payload or {},
                "safe_details": operation["safe_details"],
            },
        )
        return operation

    def network_operations_payload(self) -> dict:
        return {
            "operations": [
                operation.to_payload()
                for operation in self._network_helper.list_operations()
            ]
        }

    def set_dashboard_page_enabled(self, page_id: str, enabled: bool) -> dict:
        page = page_id.strip()
        if not page:
            raise ValueError("page_id is required")
        result = asdict(self._client.set_page_enabled(page, enabled))
        self._events.record(
            source="dashboard",
            severity="info" if result["accepted"] else "warning",
            message=result["message"] or f"{page} enabled={enabled}",
            details={
                "page_id": page,
                "enabled": enabled,
                "accepted": result["accepted"],
                "error_code": result["error_code"],
            },
        )
        return result

    def events_payload(self) -> dict:
        return self._events.payload()


def _policy_input_from_network(network: NetworkStatus) -> NetworkPolicyInput:
    active_interfaces = {item.lower() for item in network.active_interfaces}
    tunnel_connected = any(item.startswith(("tun", "wg", "tailscale", "zt")) for item in active_interfaces)
    return NetworkPolicyInput(
        internet_online=network.online,
        ethernet_connected=network.ethernet_connected,
        tunnel_connected=tunnel_connected,
        wifi_connected=network.wifi_connected,
    )


def _dashboard_payload(status: DashboardStatus) -> dict:
    payload = asdict(status)
    payload["pages"] = [asdict(page) for page in status.pages]
    return payload


def _summary(
    network: NetworkStatus,
    display: DisplayStatus,
    core: dict,
    policy: NetworkPolicyDecision,
) -> dict:
    return {
        "internet": "online" if network.online else "offline",
        "access": _access_label(network, policy),
        "address": network.ip_address or "",
        "hotspot": policy.hotspot_mode,
        "core": "healthy" if core.get("healthy") else "unhealthy",
        "display": "healthy" if display.healthy else "unhealthy",
    }


def _access_label(network: NetworkStatus, policy: NetworkPolicyDecision) -> str:
    if network.connection_type == "wifi" and network.wifi_ssid:
        return f"Wi-Fi: {network.wifi_ssid}"
    if network.connection_type == "wifi":
        return "Wi-Fi"
    if network.connection_type == "ethernet":
        return "Ethernet"
    if policy.state == "online_tunnel_hotspot":
        return "Tunnel"
    if policy.hotspot_mode != "off":
        return "Hotspot"
    return "Unknown"
