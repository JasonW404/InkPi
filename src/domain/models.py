"""Domain data models used across services, UI, and scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class GitHubContributionDay:
    """Single-day GitHub contribution summary."""

    day: date
    commit_count: int


@dataclass(frozen=True)
class GitHubMonthlyStats:
    """Monthly GitHub statistics shown on the dashboard."""

    month: str
    contributions: list[GitHubContributionDay]
    organization_repo_count: int
    organization_monthly_commit_count: int
    organization_additions: int
    organization_deletions: int


@dataclass(frozen=True)
class DateTimeInfo:
    """Current datetime payload for display."""

    now: datetime
    timezone: str


@dataclass(frozen=True)
class WeatherInfo:
    """Current weather payload for display."""

    summary: str
    temperature_celsius: float | None
    apparent_temperature_celsius: float | None
    updated_at: datetime


@dataclass(frozen=True)
class SystemStatus:
    """System load snapshot."""

    load_percent: float
    load_level: int


@dataclass(frozen=True)
class KnowledgeCard:
    """Knowledge card item rendered in the right-top panel."""

    title: str
    body: str
    source: str
    updated_at: datetime


@dataclass(frozen=True)
class DashboardSnapshot:
    """Aggregated dashboard data for one refresh cycle."""

    generated_at: datetime
    date_time: DateTimeInfo
    weather: WeatherInfo
    system: SystemStatus
    github: GitHubMonthlyStats
    card: KnowledgeCard
