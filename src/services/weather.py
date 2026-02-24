"""Weather provider service with Open-Meteo integration and fallback."""

from __future__ import annotations

from datetime import UTC, datetime

import requests

from src.config import AppConfig
from src.domain.models import WeatherInfo


class WeatherService:
	"""Fetch and normalize weather data for dashboard rendering."""

	def __init__(self, config: AppConfig) -> None:
		"""Store weather provider configuration.

		Args:
			config: Application configuration.
		"""

		self._location = config.weather.location
		self._provider = config.weather.provider
		self._timeout_seconds = 8

	def get_current(self) -> WeatherInfo:
		"""Fetch current weather information.

		Returns:
			Current weather payload or fallback payload on failure.
		"""

		if self._provider != "open-meteo":
			return self._fallback("unsupported_provider")

		coordinates = self._parse_coordinates(self._location)
		if coordinates is None:
			return self._fallback("invalid_location")

		latitude, longitude = coordinates
		try:
			response = requests.get(
				"https://api.open-meteo.com/v1/forecast",
				params={
					"latitude": latitude,
					"longitude": longitude,
					"current": "temperature_2m,apparent_temperature,weather_code",
					"timezone": "auto",
				},
				timeout=self._timeout_seconds,
			)
			response.raise_for_status()
			payload = response.json()
			current = payload.get("current", {})
			return WeatherInfo(
				summary=f"code:{current.get('weather_code', 'n/a')}",
				temperature_celsius=self._to_float_or_none(current.get("temperature_2m")),
				apparent_temperature_celsius=self._to_float_or_none(
					current.get("apparent_temperature")
				),
				updated_at=datetime.now(UTC),
			)
		except requests.RequestException:
			return self._fallback("network_error")

	def _fallback(self, reason: str) -> WeatherInfo:
		"""Build fallback weather payload.

		Args:
			reason: Failure reason label.

		Returns:
			Fallback weather payload.
		"""

		return WeatherInfo(
			summary=f"unavailable:{reason}",
			temperature_celsius=None,
			apparent_temperature_celsius=None,
			updated_at=datetime.now(UTC),
		)

	@staticmethod
	def _parse_coordinates(value: str) -> tuple[float, float] | None:
		"""Parse location string to latitude and longitude tuple."""

		if "," not in value:
			return None
		parts = [part.strip() for part in value.split(",", maxsplit=1)]
		try:
			return float(parts[0]), float(parts[1])
		except ValueError:
			return None

	@staticmethod
	def _to_float_or_none(value: object) -> float | None:
		"""Convert scalar value to float when possible."""

		if value is None:
			return None
		try:
			return float(value)
		except (TypeError, ValueError):
			return None

