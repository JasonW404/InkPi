"""Application runtime orchestration for dashboard refresh cycles."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum

from src.config import AppConfig
from src.services.dashboard import DashboardDataService
from src.services.datetime import DateTimeService
from src.services.github import GitHubService
from src.services.posts import KnowledgeCardService
from src.services.system import SystemService
from src.services.weather import WeatherService
from src.ui.renderer import DashboardRenderer


class RefreshMode(str, Enum):
    """Supported display refresh modes."""

    PARTIAL = "partial"
    FULL = "full"


@dataclass(frozen=True)
class RefreshDecision:
    """Decision object describing the current refresh action."""

    mode: RefreshMode
    reason: str


class RefreshPolicy:
    """Stateful policy that selects partial or full refresh."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize policy state.

        Args:
            config: Application configuration.
        """

        self._config = config
        self._last_full_refresh_monotonic = time.monotonic()
        self._partial_refresh_count = 0

    @property
    def sleep_seconds(self) -> int:
        """Return sleep interval between cycles in seconds."""

        return self._config.refresh.partial_refresh_interval_seconds

    def decide(self) -> RefreshDecision:
        """Return next refresh decision based on elapsed time and counters."""

        now = time.monotonic()
        elapsed_since_full = now - self._last_full_refresh_monotonic

        if elapsed_since_full >= self._config.refresh.full_refresh_interval_seconds:
            self._mark_full_refresh(now)
            return RefreshDecision(
                mode=RefreshMode.FULL,
                reason="full_refresh_interval_elapsed",
            )

        if (
            self._partial_refresh_count
            >= self._config.refresh.max_partial_refreshes_before_full
        ):
            self._mark_full_refresh(now)
            return RefreshDecision(
                mode=RefreshMode.FULL,
                reason="partial_refresh_threshold_reached",
            )

        self._partial_refresh_count += 1
        return RefreshDecision(mode=RefreshMode.PARTIAL, reason="regular_partial_refresh")

    def _mark_full_refresh(self, now: float) -> None:
        """Reset full-refresh baseline and partial-refresh counter.

        Args:
            now: Current monotonic timestamp.
        """

        self._last_full_refresh_monotonic = now
        self._partial_refresh_count = 0


class DashboardApplication:
    """Main application loop that collects data and schedules refresh."""

    def __init__(self, config: AppConfig) -> None:
        """Create runtime dependencies.

        Args:
            config: Application configuration.
        """

        self._config = config
        self._policy = RefreshPolicy(config)
        self._data_service = DashboardDataService(
            date_time_provider=DateTimeService(config),
            weather_provider=WeatherService(config),
            system_provider=SystemService(),
            github_provider=GitHubService(config),
            card_provider=KnowledgeCardService(config),
        )
        self._renderer = DashboardRenderer(
            github_username=config.github.username,
            github_organization=config.github.organization,
        )
        self._logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        """Start infinite dashboard runtime loop."""

        self._logger.info(
            "dashboard_started screen=%sx%s partial=%ss full=%ss max_partial=%s",
            self._config.screen.width,
            self._config.screen.height,
            self._config.refresh.partial_refresh_interval_seconds,
            self._config.refresh.full_refresh_interval_seconds,
            self._config.refresh.max_partial_refreshes_before_full,
        )

        while True:
            decision = self._policy.decide()
            snapshot = self._data_service.collect()
            
            # Render dashboard image.
            image = self._renderer.render(snapshot)
            
            # TODO: Send image to display adapter for actual screen refresh.
            # For now, just log rendering success.
            
            self._logger.info(
                "refresh mode=%s reason=%s tz=%s load_level=%s repos=%s commits=%s rendered=%sx%s",
                decision.mode,
                decision.reason,
                snapshot.date_time.timezone,
                snapshot.system.load_level,
                snapshot.github.organization_repo_count,
                snapshot.github.organization_monthly_commit_count,
                image.width,
                image.height,
            )
            time.sleep(self._policy.sleep_seconds)
