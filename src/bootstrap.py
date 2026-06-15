"""Composition root utilities for constructing app runtime dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from src.adapters.github_api import GitHubApiAdapter
from src.adapters.knowledge_cards import KnowledgeCardRemoteAdapter
from src.adapters.open_meteo import OpenMeteoAdapter
from src.config import AppConfig
from src.display.adapter import EPDAdapter
from src.display.dirty_region import DirtyRegionTracker
from src.services.dashboard import DashboardDataService
from src.services.contracts import SystemStatusProvider
from src.services.datetime import DateTimeService
from src.services.github import GitHubService
from src.services.posts import KnowledgeCardService
from src.services.system import SystemService
from src.services.weather import WeatherService
from src.ui.lifecycle_renderer import LifecycleScreenRenderer
from src.ui.renderer import DashboardRenderer


@dataclass(frozen=True)
class RuntimeComponents:
    """Concrete runtime dependency set for dashboard loop."""

    data_service: DashboardDataService
    renderer: DashboardRenderer
    lifecycle_renderer: LifecycleScreenRenderer
    display: EPDAdapter
    dirty_tracker: DirtyRegionTracker


def build_data_service(
    config: AppConfig,
    system_provider: SystemStatusProvider | None = None,
) -> DashboardDataService:
    """Build shared dashboard data service used by runtime and preview modes."""

    weather_adapter = OpenMeteoAdapter(timeout_seconds=8)
    github_adapter = GitHubApiAdapter(api_key=config.github.api_key, timeout_seconds=12)
    knowledge_card_adapter = KnowledgeCardRemoteAdapter(timeout_seconds=8)

    return DashboardDataService(
        date_time_provider=DateTimeService(config),
        weather_provider=WeatherService(config, meteo_adapter=weather_adapter),
        system_provider=system_provider or SystemService(),
        github_provider=GitHubService(config, api_adapter=github_adapter),
        card_provider=KnowledgeCardService(config, remote_adapter=knowledge_card_adapter),
    )


def build_renderer(config: AppConfig) -> DashboardRenderer:
    """Build dashboard renderer from application configuration."""

    return DashboardRenderer(
        github_username=config.github.username,
        github_organization=config.github.organization,
    )


def build_runtime_components(config: AppConfig) -> RuntimeComponents:
    """Build concrete dependencies for hardware runtime loop."""

    return RuntimeComponents(
        data_service=build_data_service(config),
        renderer=build_renderer(config),
        lifecycle_renderer=LifecycleScreenRenderer(
            width=config.screen.width,
            height=config.screen.height,
        ),
        display=EPDAdapter(
            width=config.screen.width,
            height=config.screen.height,
        ),
        dirty_tracker=DirtyRegionTracker(
            width=config.screen.width,
            height=config.screen.height,
            pixel_threshold=6,
        ),
    )
