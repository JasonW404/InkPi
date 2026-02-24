"""System resource provider service."""

from __future__ import annotations

import os

from src.domain.models import SystemStatus


class SystemService:
	"""Provide system load in percent and 20%-tier levels."""

	def get_current(self) -> SystemStatus:
		"""Read current system load and map to level.

		Returns:
			System status with load percent and level (0-5).
		"""

		cpu_count = os.cpu_count() or 1
		load_1min = os.getloadavg()[0]
		load_percent = max(0.0, (load_1min / cpu_count) * 100.0)
		load_level = min(5, max(0, int(load_percent // 20)))
		return SystemStatus(load_percent=load_percent, load_level=load_level)

