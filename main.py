"""Program entrypoint for running the eInk dashboard service."""

import logging

from src.app import DashboardApplication
from src.config import AppConfig


def main() -> None:
    """Configure logging, load config, and run the dashboard."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    config = AppConfig.from_env()
    app = DashboardApplication(config)
    app.run()


if __name__ == "__main__":
    main()
