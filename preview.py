"""Generate dashboard preview with real data sources."""

from __future__ import annotations

import logging
from pathlib import Path

from src.config import AppConfig
from src.services.dashboard import DashboardDataService
from src.services.datetime import DateTimeService
from src.services.github import GitHubService
from src.services.posts import KnowledgeCardService
from src.services.system import SystemService
from src.services.weather import WeatherService
from src.ui.renderer import DashboardRenderer


def main() -> None:
    """Generate preview image with real data and save to file."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

    print("Loading configuration...")
    try:
        config = AppConfig.from_env()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        logger.info("Hint: Set environment variables like EINK_GITHUB_USERNAME, etc.")
        raise

    print("Initializing data services...")
    data_service = DashboardDataService(
        date_time_provider=DateTimeService(config),
        weather_provider=WeatherService(config),
        system_provider=SystemService(),
        github_provider=GitHubService(config),
        card_provider=KnowledgeCardService(config),
    )

    print("Collecting real data from all sources...")
    try:
        snapshot = data_service.collect()
    except Exception as e:
        logger.error(f"Failed to collect data: {e}")
        raise

    print("Rendering dashboard...")
    renderer = DashboardRenderer(
        github_username=config.github.username,
        github_organization=config.github.organization,
    )
    image = renderer.render(snapshot)

    output_path = Path("preview.png")
    image.save(output_path)
    
    print(f"\n✓ Preview saved to: {output_path.absolute()}")
    print(f"  - DateTime: {snapshot.date_time.now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Weather info (handle None temperature)
    if snapshot.weather.temperature_celsius is not None:
        print(f"  - Weather: {snapshot.weather.temperature_celsius:.1f}°C")
    else:
        print(f"  - Weather: {snapshot.weather.summary}")
    
    print(f"  - System Load: {snapshot.system.load_level}/5 ({snapshot.system.load_percent:.1f}%)")
    print(f"  - GitHub Contributions: {len(snapshot.github.contributions)} days")
    print(f"  - GitHub Org Repos: {snapshot.github.organization_repo_count}")
    print(f"  - Knowledge Card: {snapshot.card.title[:40]}...")


if __name__ == "__main__":
    main()
