from __future__ import annotations

from src.bootstrap import build_data_service
from src.services.dashboard import DashboardDataService

from conftest import (
    make_config,
    sample_card,
    sample_datetime,
    sample_github,
    sample_system,
    sample_weather,
)


class DateTimeProviderFake:
    def get_current(self):
        return sample_datetime()


class WeatherProviderFake:
    def get_current(self):
        return sample_weather()


class SystemProviderFake:
    def get_current(self):
        return sample_system()


class GitHubProviderFake:
    def get_monthly_stats(self):
        return sample_github()


class CardProviderFake:
    def get_current(self):
        return sample_card()


def test_dashboard_data_service_collects_complete_snapshot() -> None:
    service = DashboardDataService(
        date_time_provider=DateTimeProviderFake(),
        weather_provider=WeatherProviderFake(),
        system_provider=SystemProviderFake(),
        github_provider=GitHubProviderFake(),
        card_provider=CardProviderFake(),
    )

    snapshot = service.collect()

    assert snapshot.date_time.timezone == "UTC"
    assert snapshot.weather.summary == "clear"
    assert snapshot.system.load_level == 1
    assert snapshot.github.organization_repo_count == 2
    assert snapshot.card.title == "Sample"


def test_bootstrap_build_data_service_returns_aggregator() -> None:
    config = make_config()
    service = build_data_service(config)

    assert isinstance(service, DashboardDataService)
