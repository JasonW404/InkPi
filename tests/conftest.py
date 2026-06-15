from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import (
    AppConfig,
    GitHubConfig,
    KnowledgeCardConfig,
    RefreshConfig,
    ScreenConfig,
    WeatherConfig,
)
from src.domain.models import (
    DateTimeInfo,
    GitHubMonthlyStats,
    KnowledgeCard,
    SystemStatus,
    WeatherInfo,
)


def make_config(
    *,
    weather_provider: str = "open-meteo",
    weather_location: str = "Shanghai",
    github_username: str = "tester",
    github_org: str = "test-org",
    github_token: str = "token",
    knowledge_local_file: str = "data/cards.json",
    knowledge_remote_enabled: bool = False,
    knowledge_remote_url: str = "",
    partial_interval: int = 60,
    full_interval: int = 3600,
    max_partial_before_full: int = 30,
    ghosting_mode: str = "balanced",
) -> AppConfig:
    return AppConfig(
        screen=ScreenConfig(),
        refresh=RefreshConfig(
            partial_refresh_interval_seconds=partial_interval,
            full_refresh_interval_seconds=full_interval,
            max_partial_refreshes_before_full=max_partial_before_full,
            ghosting_mode=ghosting_mode,
        ),
        github=GitHubConfig(
            username=github_username,
            organization=github_org,
            api_key=github_token,
        ),
        weather=WeatherConfig(
            location=weather_location,
            provider=weather_provider,
        ),
        knowledge_card=KnowledgeCardConfig(
            local_file=knowledge_local_file,
            remote_enabled=knowledge_remote_enabled,
            remote_url=knowledge_remote_url,
        ),
    )


def sample_datetime() -> DateTimeInfo:
    return DateTimeInfo(now=datetime.now(UTC), timezone="UTC")


def sample_weather() -> WeatherInfo:
    return WeatherInfo(
        summary="clear",
        temperature_celsius=20.0,
        apparent_temperature_celsius=19.0,
        updated_at=datetime.now(UTC),
    )


def sample_system() -> SystemStatus:
    return SystemStatus(
        cpu_average_percent=10.0,
        cpu_peak_percent=20.0,
        cpu_per_core_percent=[10.0, 20.0],
        memory_used_gb=1.2,
        memory_total_gb=4.0,
        memory_percent=30.0,
        global_load_percent=25.0,
        load_level=1,
    )


def sample_github() -> GitHubMonthlyStats:
    return GitHubMonthlyStats(
        month="2026-02",
        contributions=[],
        user_monthly_code_lines=100,
        organization_repo_count=2,
        organization_monthly_commit_count=8,
        organization_monthly_code_lines=200,
        organization_additions=120,
        organization_deletions=80,
    )


def sample_card() -> KnowledgeCard:
    return KnowledgeCard(
        title="Sample",
        body="Body",
        source="test",
        updated_at=datetime.now(UTC),
    )
