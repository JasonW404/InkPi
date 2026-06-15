"""Weather provider service with Open-Meteo integration and geocoding."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from src.adapters.contracts import OpenMeteoClient
from src.config import AppConfig
from src.domain.models import WeatherInfo


class WeatherService:
	"""Fetch and normalize weather data for dashboard rendering."""

	def __init__(self, config: AppConfig, meteo_adapter: OpenMeteoClient) -> None:
		"""Store weather provider configuration.

		Args:
			config: Application configuration.
			meteo_adapter: Open-Meteo integration adapter.
		"""

		self._location = config.weather.location
		self._provider = config.weather.provider
		self._adapter = meteo_adapter
		self._logger = logging.getLogger(self.__class__.__name__)
		
		# Cache geocoded coordinates to avoid repeated API calls.
		self._cached_coordinates: tuple[float, float] | None = None
		self._cached_weather: WeatherInfo | None = None
		self._cached_weather_monotonic: float = 0.0
		self._weather_cache_ttl_seconds = 15

	def get_current(self) -> WeatherInfo:
		"""Fetch current weather information.

		Returns:
			Current weather payload or fallback payload on failure.
		"""

		now_mono = time.monotonic()
		if (
			self._cached_weather is not None
			and now_mono - self._cached_weather_monotonic < self._weather_cache_ttl_seconds
		):
			return self._cached_weather

		if self._provider != "open-meteo":
			return self._fallback("unsupported_provider")

		# Resolve location to coordinates (with caching).
		if self._cached_coordinates is None:
			self._cached_coordinates = self._resolve_location(self._location)
		
		if self._cached_coordinates is None:
			return self._fallback("invalid_location")

		latitude, longitude = self._cached_coordinates
		payload = self._adapter.fetch_current_weather(latitude, longitude)
		if payload is None:
			fallback = self._fallback("network_error")
			self._cached_weather = fallback
			self._cached_weather_monotonic = now_mono
			return fallback

		current = payload.get("current", {})
		weather_info = WeatherInfo(
			summary=f"code:{current.get('weather_code', 'n/a')}",
			temperature_celsius=self._to_float_or_none(current.get("temperature_2m")),
			apparent_temperature_celsius=self._to_float_or_none(
				current.get("apparent_temperature")
			),
			updated_at=datetime.now(UTC),
		)
		self._cached_weather = weather_info
		self._cached_weather_monotonic = now_mono
		return weather_info

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
		"""Parse location string as latitude,longitude coordinates.
		
		Args:
			value: Coordinate string in "lat,lon" format.
		
		Returns:
			Tuple of (latitude, longitude) or None if invalid.
		"""

		if "," not in value:
			return None
		parts = [part.strip() for part in value.split(",", maxsplit=1)]
		try:
			return float(parts[0]), float(parts[1])
		except ValueError:
			return None

	def _resolve_location(self, location: str) -> tuple[float, float] | None:
		"""Resolve location string to coordinates.
		
		Tries to parse as coordinates first, then falls back to geocoding.
		
		Args:
			location: Location string (coordinates or place name).
		
		Returns:
			Tuple of (latitude, longitude) or None if unresolvable.
		"""

		if not location or not location.strip():
			return None
		
		# First try parsing as coordinates.
		coordinates = self._parse_coordinates(location)
		if coordinates is not None:
			self._logger.info(f"Parsed location as coordinates: {coordinates}")
			return coordinates
		
		# Fall back to geocoding the place name.
		self._logger.info(f"Geocoding location: {location}")
		return self._geocode_location(location)

	def _geocode_location(self, place_name: str) -> tuple[float, float] | None:
		"""Geocode a place name to coordinates using Open-Meteo Geocoding API.
		
		Args:
			place_name: Name of the location (e.g., "上海市青浦区").
		
		Returns:
			Tuple of (latitude, longitude) or None if geocoding fails.
		"""

		data = self._adapter.geocode(place_name=place_name, language="zh")
		if data is None:
			self._logger.warning(f"Geocoding request failed: {place_name}")
			return None

		results = data.get("results", [])
		if not results:
			self._logger.warning(f"No geocoding results for: {place_name}")
			return None

		result = results[0]
		latitude = result.get("latitude")
		longitude = result.get("longitude")
		location_name = result.get("name", "")
		country = result.get("country", "")

		if latitude is None or longitude is None:
			self._logger.warning(f"Invalid geocoding result for: {place_name}")
			return None

		self._logger.info(
			f"Geocoded '{place_name}' to {location_name}, {country} "
			f"({latitude:.4f}, {longitude:.4f})"
		)
		return (float(latitude), float(longitude))

	@staticmethod
	def _to_float_or_none(value: object) -> float | None:
		"""Convert scalar value to float when possible."""

		if value is None:
			return None
		try:
			return float(value)
		except (TypeError, ValueError):
			return None

