"""Datetime provider service with timezone support."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.config import AppConfig
from src.domain.models import DateTimeInfo


class DateTimeService:
	"""Provide current datetime based on configured timezone."""

	def __init__(self, config: AppConfig) -> None:
		"""Store timezone configuration.

		Args:
			config: Application configuration.
		"""

		self._timezone_name = config.weather.timezone

	def get_current(self) -> DateTimeInfo:
		"""Return current datetime payload.

		Returns:
			Timezone-aware datetime information.
		"""

		try:
			tz = ZoneInfo(self._timezone_name)
		except ZoneInfoNotFoundError:
			tz = ZoneInfo("UTC")
		now = datetime.now(tz)
		return DateTimeInfo(now=now, timezone=str(now.tzinfo))

