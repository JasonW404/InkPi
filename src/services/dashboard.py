"""Dashboard data aggregation service."""

from __future__ import annotations

from datetime import UTC, datetime

from src.domain.models import DashboardSnapshot
from src.services.contracts import (
    DateTimeProvider,
    GitHubProvider,
    KnowledgeCardProvider,
    SystemStatusProvider,
    WeatherProvider,
)


class DashboardDataService:
    """Aggregate data from all providers into one snapshot."""

    def __init__(
        self,
        date_time_provider: DateTimeProvider,
        weather_provider: WeatherProvider,
        system_provider: SystemStatusProvider,
        github_provider: GitHubProvider,
        card_provider: KnowledgeCardProvider,
    ) -> None:
        """Create aggregator with provider dependencies.

        Args:
            date_time_provider: Datetime data provider.
            weather_provider: Weather data provider.
            system_provider: System status provider.
            github_provider: GitHub statistics provider.
            card_provider: Knowledge card provider.
        """

        self._date_time_provider = date_time_provider
        self._weather_provider = weather_provider
        self._system_provider = system_provider
        self._github_provider = github_provider
        self._card_provider = card_provider

    def collect(self) -> DashboardSnapshot:
        """Collect a full dashboard snapshot for one cycle.

        Returns:
            Aggregated dashboard snapshot.
        """

        return DashboardSnapshot(
            generated_at=datetime.now(UTC),
            date_time=self._date_time_provider.get_current(),
            weather=self._weather_provider.get_current(),
            system=self._system_provider.get_current(),
            github=self._github_provider.get_monthly_stats(),
            card=self._card_provider.get_current(),
        )
