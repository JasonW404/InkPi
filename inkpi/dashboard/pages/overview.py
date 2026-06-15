"""Existing information dashboard exposed as an InkPi page."""

from __future__ import annotations

from inkpi.contracts import ManagementDataProvider
from src.bootstrap import build_data_service, build_renderer
from src.config import AppConfig
from src.domain.models import SystemStatus


class ManagementSystemProvider:
    """Translate management-owned system facts for the legacy overview renderer."""

    def __init__(self, management: ManagementDataProvider) -> None:
        self._management = management

    def get_current(self) -> SystemStatus:
        facts = self._management.get_system_status()
        global_load = min(
            100.0,
            (0.5 * facts.cpu_average_percent)
            + (0.3 * facts.cpu_peak_percent)
            + (0.2 * facts.memory_percent),
        )
        return SystemStatus(
            cpu_average_percent=facts.cpu_average_percent,
            cpu_peak_percent=facts.cpu_peak_percent,
            cpu_per_core_percent=[],
            memory_used_gb=facts.memory_used_gb,
            memory_total_gb=facts.memory_total_gb,
            memory_percent=facts.memory_percent,
            global_load_percent=global_load,
            load_level=min(5, max(0, int(global_load // 20))),
        )


class OverviewPage:
    page_id = "overview"
    name = "Overview"

    def __init__(self, management: ManagementDataProvider | None = None) -> None:
        config = AppConfig.from_env()
        system_provider = ManagementSystemProvider(management) if management else None
        self._data = build_data_service(config, system_provider=system_provider)
        self._renderer = build_renderer(config)

    def collect(self):
        return self._data.collect()

    def render(self, snapshot):
        return self._renderer.render(snapshot)
