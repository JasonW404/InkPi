"""System resource provider service."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from src.domain.models import SystemStatus


@dataclass(frozen=True)
class _CpuTimes:
	"""CPU aggregate and idle jiffies for one snapshot."""

	total: int
	idle: int


class SystemService:
	"""Provide CPU and memory load metrics.

	CPU is derived from `/proc/stat` deltas for each core.
	Memory usage is derived from `/proc/meminfo` using MemTotal - MemAvailable.
	"""

	def __init__(self) -> None:
		"""Initialize internal state for CPU delta sampling."""

		self._previous_cpu_samples: list[_CpuTimes] | None = None

	def get_current(self) -> SystemStatus:
		"""Read current CPU/memory load and map to global level.

		Returns:
			System status with CPU, memory and global load metrics.
		"""

		cpu_per_core = self._read_cpu_per_core_percent()
		cpu_average = sum(cpu_per_core) / len(cpu_per_core) if cpu_per_core else 0.0
		cpu_peak = max(cpu_per_core) if cpu_per_core else 0.0

		memory_used_gb, memory_total_gb, memory_percent = self._read_memory_metrics()

		# Global load algorithm:
		# - 50% average CPU pressure
		# - 30% peak CPU pressure (highlight hot core)
		# - 20% memory pressure
		global_load_percent = min(
			100.0,
			(0.5 * cpu_average) + (0.3 * cpu_peak) + (0.2 * memory_percent),
		)
		load_level = min(5, max(0, int(global_load_percent // 20)))

		return SystemStatus(
			cpu_average_percent=cpu_average,
			cpu_peak_percent=cpu_peak,
			cpu_per_core_percent=cpu_per_core,
			memory_used_gb=memory_used_gb,
			memory_total_gb=memory_total_gb,
			memory_percent=memory_percent,
			global_load_percent=global_load_percent,
			load_level=load_level,
		)

	def _read_cpu_per_core_percent(self) -> list[float]:
		"""Read per-core CPU usage percent using /proc/stat deltas."""

		current = self._read_cpu_samples()
		if self._previous_cpu_samples is None:
			self._previous_cpu_samples = current
			return [0.0 for _ in current]

		usage_values: list[float] = []
		for previous, now in zip(self._previous_cpu_samples, current, strict=False):
			total_delta = now.total - previous.total
			idle_delta = now.idle - previous.idle
			if total_delta <= 0:
				usage_values.append(0.0)
				continue
			busy_delta = max(0, total_delta - idle_delta)
			usage = (busy_delta / total_delta) * 100.0
			usage_values.append(max(0.0, min(100.0, usage)))

		self._previous_cpu_samples = current
		return usage_values

	def _read_cpu_samples(self) -> list[_CpuTimes]:
		"""Read per-core CPU counters from /proc/stat."""

		if not Path("/proc/stat").exists():
			return [_CpuTimes(total=1, idle=1) for _ in range(os.cpu_count() or 1)]

		samples: list[_CpuTimes] = []
		with open("/proc/stat", "r", encoding="utf-8") as stat_file:
			for line in stat_file:
				parts = line.split()
				if not parts:
					continue
				label = parts[0]
				if not label.startswith("cpu") or label == "cpu":
					continue
				values = [int(value) for value in parts[1:]]
				total = sum(values)
				idle = values[3] + (values[4] if len(values) > 4 else 0)
				samples.append(_CpuTimes(total=total, idle=idle))
		return samples

	def _read_memory_metrics(self) -> tuple[float, float, float]:
		"""Read memory usage (GB and percent) from /proc/meminfo."""

		if not Path("/proc/meminfo").exists():
			try:
				total_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
			except (OSError, ValueError):
				total_bytes = 0
			total_gb = total_bytes / (1024**3)
			return 0.0, total_gb, 0.0

		mem_kb: dict[str, int] = {}
		with open("/proc/meminfo", "r", encoding="utf-8") as meminfo_file:
			for line in meminfo_file:
				key, raw = line.split(":", maxsplit=1)
				mem_kb[key] = int(raw.strip().split()[0])

		total_kb = max(1, mem_kb.get("MemTotal", 0))
		available_kb = mem_kb.get("MemAvailable", 0)
		used_kb = max(0, total_kb - available_kb)

		memory_total_gb = total_kb / (1024 * 1024)
		memory_used_gb = used_kb / (1024 * 1024)
		memory_percent = (used_kb / total_kb) * 100.0

		return memory_used_gb, memory_total_gb, max(0.0, min(100.0, memory_percent))
