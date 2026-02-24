"""Generate dashboard preview for layout verification."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.domain.models import (
    DashboardSnapshot,
    DateTimeInfo,
    GitHubContributionDay,
    GitHubMonthlyStats,
    KnowledgeCard,
    SystemStatus,
    WeatherInfo,
)
from src.ui.renderer import DashboardRenderer


def create_sample_snapshot() -> DashboardSnapshot:
    """Create sample dashboard data for preview.

    Returns:
        Mock dashboard snapshot with representative data.
    """
    now = datetime.now(UTC)

    return DashboardSnapshot(
        generated_at=now,
        date_time=DateTimeInfo(now=now, timezone="UTC"),
        weather=WeatherInfo(
            summary="Partly cloudy",
            temperature_celsius=18.5,
            apparent_temperature_celsius=17.2,
            updated_at=now,
        ),
        system=SystemStatus(load_percent=42.3, load_level=2),
        github=GitHubMonthlyStats(
            month="2026-02",
            contributions=[
                GitHubContributionDay(day=now.date(), commit_count=3),
                GitHubContributionDay(day=now.date(), commit_count=5),
                GitHubContributionDay(day=now.date(), commit_count=1),
                GitHubContributionDay(day=now.date(), commit_count=8),
                GitHubContributionDay(day=now.date(), commit_count=2),
                GitHubContributionDay(day=now.date(), commit_count=0),
                GitHubContributionDay(day=now.date(), commit_count=4),
            ],
            organization_repo_count=12,
            organization_monthly_commit_count=47,
            organization_additions=1523,
            organization_deletions=892,
        ),
        card=KnowledgeCard(
            title="Sample Knowledge Card",
            body="This is a demonstration of the dashboard layout. "
            "Knowledge cards can display useful information, tips, or quotes. "
            "The content wraps automatically to fit the panel dimensions.",
            source="preview-script",
            updated_at=now,
        ),
    )


def main() -> None:
    """Generate preview image and save to file."""
    print("Generating dashboard preview...")

    snapshot = create_sample_snapshot()
    renderer = DashboardRenderer(github_username="sample-user", github_organization="sample-org")
    image = renderer.render(snapshot)

    output_path = Path("preview.png")
    image.save(output_path)
    print(f"Preview saved to: {output_path.absolute()}")


if __name__ == "__main__":
    main()
