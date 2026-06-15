"""Refresh scheduling policy for dashboard runtime loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time

from src.config import AppConfig


class RefreshMode(str, Enum):
    """Supported display refresh modes."""

    PARTIAL = "partial"
    FULL = "full"


@dataclass(frozen=True)
class RefreshDecision:
    """Decision object describing current refresh action."""

    mode: RefreshMode
    reason: str


class RefreshPolicy:
    """Stateful policy that selects partial or full refresh."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize policy state.

        Args:
            config: Application configuration.
        """

        self._config = config
        self._last_full_refresh_monotonic = time.monotonic()
        self._partial_refresh_count = 0

    @property
    def sleep_seconds(self) -> int:
        """Return sleep interval between cycles in seconds."""

        return self._config.refresh.partial_refresh_interval_seconds

    def decide(self) -> RefreshDecision:
        """Return next refresh decision based on elapsed time and counters."""

        now = time.monotonic()
        elapsed_since_full = now - self._last_full_refresh_monotonic

        if elapsed_since_full >= self._config.refresh.full_refresh_interval_seconds:
            self._mark_full_refresh(now)
            return RefreshDecision(
                mode=RefreshMode.FULL,
                reason="full_refresh_interval_elapsed",
            )

        if (
            self._partial_refresh_count
            >= self._config.refresh.max_partial_refreshes_before_full
        ):
            self._mark_full_refresh(now)
            return RefreshDecision(
                mode=RefreshMode.FULL,
                reason="partial_refresh_threshold_reached",
            )

        self._partial_refresh_count += 1
        return RefreshDecision(mode=RefreshMode.PARTIAL, reason="regular_partial_refresh")

    def mark_external_full_refresh(self) -> None:
        """Sync policy state after a full refresh outside regular policy decisions."""

        self._mark_full_refresh(time.monotonic())

    def _mark_full_refresh(self, now: float) -> None:
        """Reset full-refresh baseline and partial-refresh counter.

        Args:
            now: Current monotonic timestamp.
        """

        self._last_full_refresh_monotonic = now
        self._partial_refresh_count = 0
