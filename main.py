"""Program entrypoint for hardware mode and preview rendering."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.app import DashboardApplication
from src.config import AppConfig
from src.services.dashboard import DashboardDataService
from src.services.datetime import DateTimeService
from src.services.github import GitHubService
from src.services.posts import KnowledgeCardService
from src.services.system import SystemService
from src.services.weather import WeatherService
from src.ui.renderer import DashboardRenderer


def _build_data_service(config: AppConfig) -> DashboardDataService:
    """Build shared dashboard data service used by runtime and preview modes."""

    return DashboardDataService(
        date_time_provider=DateTimeService(config),
        weather_provider=WeatherService(config),
        system_provider=SystemService(),
        github_provider=GitHubService(config),
        card_provider=KnowledgeCardService(config),
    )


def preview(output_path: str = "preview.png") -> Path:
    """Render one dashboard frame to an image file and return output path."""

    logger = logging.getLogger(__name__)
    config = AppConfig.from_env()

    data_service = _build_data_service(config)
    snapshot = data_service.collect()

    renderer = DashboardRenderer(
        github_username=config.github.username,
        github_organization=config.github.organization,
    )
    image = renderer.render(snapshot)

    target = Path(output_path)
    image.save(target)

    logger.info("preview_saved path=%s", target.resolve())
    logger.info(
        "preview_summary tz=%s weather=%s repos=%s commits=%s",
        snapshot.date_time.timezone,
        (
            f"{snapshot.weather.temperature_celsius:.1f}C"
            if snapshot.weather.temperature_celsius is not None
            else snapshot.weather.summary
        ),
        snapshot.github.organization_repo_count,
        snapshot.github.organization_monthly_commit_count,
    )
    return target


def run_hardware() -> None:
    """Run dashboard in hardware/epd mode."""

    config = AppConfig.from_env()
    app = DashboardApplication(config)
    app.run()


def main() -> None:
    """Parse startup args and run in hardware mode (default) or preview mode."""

    parser = argparse.ArgumentParser(description="eInk Dashboard entrypoint")
    parser.add_argument(
        "--preview",
        nargs="?",
        const="preview.png",
        default=None,
        metavar="OUTPUT",
        help=(
            "Render preview image instead of hardware runtime. "
            "Optional output path (default: preview.png)."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if args.preview is not None:
        preview(output_path=args.preview)
        return

    run_hardware()


if __name__ == "__main__":
    main()
