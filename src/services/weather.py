"""Weather provider service with Open-Meteo integration and geocoding."""

from __future__ import annotations

import logging
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
		self._logger = logging.getLogger(self.__class__.__name__)
		
		# Cache geocoded coordinates to avoid repeated API calls.
		self._cached_coordinates: tuple[float, float] | None = None

	def get_current(self) -> WeatherInfo:
		"""Fetch current weather information.

		Returns:
			Current weather payload or fallback payload on failure.
		"""

		if self._provider != "open-meteo":
			return self._fallback("unsupported_provider")

		# Resolve location to coordinates (with caching).
		if self._cached_coordinates is None:
			self._cached_coordinates = self._resolve_location(self._location)
		
		if self._cached_coordinates is None:
			return self._fallback("invalid_location")

		latitude, longitude = self._cached_coordinates
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

		try:
			response = requests.get(
				"https://geocoding-api.open-meteo.com/v1/search",
				params={
					"name": place_name,
					"count": 1,
					"language": "zh",  # Support Chinese place names.
					"format": "json",
				},
				timeout=self._timeout_seconds,
			)
			response.raise_for_status()
			data = response.json()
			
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
			
		except requests.RequestException as e:
			self._logger.warning(f"Geocoding request failed: {e}")
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

