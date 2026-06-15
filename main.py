"""Legacy compatibility entrypoint for overview preview rendering."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.bootstrap import build_data_service, build_renderer
from src.config import AppConfig


def preview(output_path: str = "preview.png") -> Path:
    """Render one dashboard frame to an image file and return output path."""

    logger = logging.getLogger(__name__)
    config = AppConfig.from_env()

    data_service = build_data_service(config)
    snapshot = data_service.collect()

    renderer = build_renderer(config)
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
    """Reject the retired monolithic hardware runtime."""

    raise SystemExit(
        "Direct hardware mode was retired by InkPi. "
        "Run `inkpi-display` and `inkpi-core`, or install the systemd services."
    )


def main() -> None:
    """Parse startup args and run in hardware mode (default) or preview mode."""

    parser = argparse.ArgumentParser(description="Legacy InkPi overview preview entrypoint")
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
