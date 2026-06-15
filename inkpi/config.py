"""Validated, atomically persisted InkPi configuration."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PageConfig:
    id: str
    enabled: bool = True


@dataclass(frozen=True)
class DashboardConfig:
    rotation_interval_seconds: int = 300
    pages: list[PageConfig] = field(
        default_factory=lambda: [PageConfig("overview"), PageConfig("codex_usage")]
    )


@dataclass(frozen=True)
class DisplayConfig:
    policy: str = "longevity"
    max_partial_refreshes: int = 5
    meaningful_change_ratio: float = 0.0005
    partial_change_ratio: float = 0.12


@dataclass(frozen=True)
class InkPiConfig:
    schema_version: int = 1
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)


class ConfigError(ValueError):
    """Raised when persisted InkPi configuration is invalid."""


def default_config_path() -> Path:
    """Return the configured state path."""

    return Path(os.getenv("INKPI_CONFIG", "~/.config/inkpi/config.json")).expanduser()


def load_config(path: str | Path | None = None) -> InkPiConfig:
    """Load configuration, returning defaults when no file exists."""

    target = Path(path).expanduser() if path else default_config_path()
    if not target.exists():
        return InkPiConfig()
    return parse_config(json.loads(target.read_text(encoding="utf-8")))


def parse_config(raw: dict[str, Any]) -> InkPiConfig:
    """Validate a raw configuration payload."""

    if raw.get("schema_version", 1) != 1:
        raise ConfigError("unsupported schema_version")

    dashboard_raw = raw.get("dashboard") or {}
    pages = [
        PageConfig(id=str(item["id"]), enabled=bool(item.get("enabled", True)))
        for item in dashboard_raw.get("pages", [{"id": "overview"}, {"id": "codex_usage"}])
    ]
    if not pages or not any(page.enabled for page in pages):
        raise ConfigError("at least one dashboard page must be enabled")
    if len({page.id for page in pages}) != len(pages):
        raise ConfigError("dashboard page ids must be unique")

    rotation = int(dashboard_raw.get("rotation_interval_seconds", 300))
    if rotation < 10:
        raise ConfigError("rotation_interval_seconds must be at least 10")

    display_raw = raw.get("display") or {}
    max_partial = int(display_raw.get("max_partial_refreshes", 5))
    if not 0 <= max_partial <= 20:
        raise ConfigError("max_partial_refreshes must be between 0 and 20")

    policy = str(display_raw.get("policy", "longevity"))
    if policy != "longevity":
        raise ConfigError("only the longevity display policy is currently supported")

    meaningful = float(display_raw.get("meaningful_change_ratio", 0.0005))
    partial = float(display_raw.get("partial_change_ratio", 0.12))
    if not 0 <= meaningful < partial <= 1:
        raise ConfigError("display change ratios are invalid")

    return InkPiConfig(
        dashboard=DashboardConfig(rotation_interval_seconds=rotation, pages=pages),
        display=DisplayConfig(
            policy=policy,
            max_partial_refreshes=max_partial,
            meaningful_change_ratio=meaningful,
            partial_change_ratio=partial,
        ),
    )


def save_config(config: InkPiConfig, path: str | Path | None = None) -> None:
    """Atomically persist validated configuration."""

    validated = parse_config(asdict(config))
    target = Path(path).expanduser() if path else default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=target.parent, delete=False
    ) as temporary:
        json.dump(asdict(validated), temporary, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.chmod(0o600)
    temporary_path.replace(target)
