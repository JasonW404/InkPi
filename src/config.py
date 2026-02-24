"""Application configuration models and environment loaders.

This module centralizes dashboard configuration and maps environment
variables to strongly typed dataclasses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _get_int(name: str, default: int) -> int:
	"""Read an integer environment variable with a default fallback.

	Args:
		name: Environment variable name.
		default: Default value when env is missing.

	Returns:
		Parsed integer value or default.
	"""

	value = os.getenv(name)
	if value is None:
		return default
	return int(value)


def _load_dotenv_file(path: str = ".env") -> None:
	"""Load key-value pairs from .env into process environment.

	Existing environment variables are not overwritten.

	Args:
		path: Dotenv file path relative to current working directory.
	"""

	dotenv_path = Path(path)
	if not dotenv_path.exists():
		return

	for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
		line = raw_line.strip()
		if not line or line.startswith("#") or "=" not in line:
			continue
		key, value = line.split("=", maxsplit=1)
		key = key.strip()
		value = value.strip().strip('"').strip("'")
		if key and key not in os.environ:
			os.environ[key] = value


@dataclass(frozen=True)
class ScreenConfig:
	"""Display hardware configuration."""

	width: int = 800
	height: int = 480
	grayscale_levels: int = 4
	orientation: str = "landscape"


@dataclass(frozen=True)
class RefreshConfig:
	"""Refresh scheduling configuration."""

	partial_refresh_interval_seconds: int = 60
	full_refresh_interval_seconds: int = 3600
	max_partial_refreshes_before_full: int = 30


@dataclass(frozen=True)
class GitHubConfig:
	"""GitHub data source configuration.

	Use `api_key` to include private repository data when permissions allow.
	"""

	username: str = "JasonW404"
	organization: str = "JasonW404-HW"
	api_key: str = ""


@dataclass(frozen=True)
class WeatherConfig:
	"""Weather source configuration.
	
	Location can be specified as:
	- Place name (e.g., "上海市青浦区", "Shanghai", "Paris, France")
	- Coordinates in "latitude,longitude" format (e.g., "31.2304,121.4737")
	"""

	location: str = ""
	timezone: str = "UTC"
	provider: str = "open-meteo"
	api_key: str = ""


@dataclass(frozen=True)
class KnowledgeCardConfig:
	"""Knowledge card source configuration."""

	local_file: str = "data/cards.json"
	remote_enabled: bool = False
	remote_url: str = ""


@dataclass(frozen=True)
class AppConfig:
	"""Top-level application configuration."""

	screen: ScreenConfig
	refresh: RefreshConfig
	github: GitHubConfig
	weather: WeatherConfig
	knowledge_card: KnowledgeCardConfig

	@classmethod
	def from_env(cls) -> "AppConfig":
		"""Build application configuration from environment variables.

		Returns:
			Fully resolved application configuration.
		"""

		_load_dotenv_file()

		return cls(
			screen=ScreenConfig(
				width=_get_int("EINK_SCREEN_WIDTH", 800),
				height=_get_int("EINK_SCREEN_HEIGHT", 480),
				grayscale_levels=_get_int("EINK_GRAYSCALE_LEVELS", 4),
				orientation=os.getenv("EINK_ORIENTATION", "landscape"),
			),
			refresh=RefreshConfig(
				partial_refresh_interval_seconds=_get_int(
					"EINK_PARTIAL_REFRESH_INTERVAL_SECONDS", 60
				),
				full_refresh_interval_seconds=_get_int(
					"EINK_FULL_REFRESH_INTERVAL_SECONDS", 3600
				),
				max_partial_refreshes_before_full=_get_int(
					"EINK_MAX_PARTIAL_REFRESHES_BEFORE_FULL", 30
				),
			),
			github=GitHubConfig(
				username=os.getenv("EINK_GITHUB_USERNAME") or GitHubConfig.username,
				organization=os.getenv("EINK_GITHUB_ORG") or GitHubConfig.organization,
				api_key=os.getenv("EINK_GITHUB_API_KEY") or os.getenv("EINK_GITHUB_TOKEN") or GitHubConfig.api_key,
			),
			weather=WeatherConfig(
				location=os.getenv("EINK_WEATHER_LOCATION", ""),
				timezone=os.getenv("EINK_TIMEZONE", "UTC"),
				provider=os.getenv("EINK_WEATHER_PROVIDER", "open-meteo"),
				api_key=os.getenv("EINK_WEATHER_API_KEY", ""),
			),
			knowledge_card=KnowledgeCardConfig(
				local_file=os.getenv("EINK_KNOWLEDGE_LOCAL_FILE", "data/cards.json"),
				remote_enabled=os.getenv("EINK_KNOWLEDGE_REMOTE_ENABLED", "0") in {"1", "true", "True"},
				remote_url=os.getenv("EINK_KNOWLEDGE_REMOTE_URL", ""),
			),
		)
