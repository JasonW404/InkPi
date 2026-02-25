"""Application runtime orchestration for dashboard refresh cycles."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum

from src.config import AppConfig
from src.display.adapter import EPDAdapter, RefreshMode as DisplayRefreshMode
from src.display.dirty_region import DirtyRegionTracker
from src.services.dashboard import DashboardDataService
from src.services.datetime import DateTimeService
from src.services.github import GitHubService
from src.services.posts import KnowledgeCardService
from src.services.system import SystemService
from src.services.weather import WeatherService
from src.ui.renderer import DashboardRenderer


class RefreshMode(str, Enum):
    """Supported display refresh modes."""

    PARTIAL = "partial"
    FULL = "full"


@dataclass(frozen=True)
class RefreshDecision:
    """Decision object describing the current refresh action."""

    mode: RefreshMode
    reason: str


@dataclass(frozen=True)
class GhostingTuning:
    """Anti-ghosting thresholds controlled by ghosting mode."""

    large_change_full_ratio: float
    partial_streak_limit: int
    small_change_ratio: float
    small_change_streak_limit: int
    overlap_iou_threshold: float
    overlap_streak_limit: int


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

    def _mark_full_refresh(self, now: float) -> None:
        """Reset full-refresh baseline and partial-refresh counter.

        Args:
            now: Current monotonic timestamp.
        """

        self._last_full_refresh_monotonic = now
        self._partial_refresh_count = 0


class DashboardApplication:
    """Main application loop that collects data and schedules refresh."""

    def __init__(self, config: AppConfig) -> None:
        """Create runtime dependencies.

        Args:
            config: Application configuration.
        """

        self._config = config
        self._policy = RefreshPolicy(config)
        self._data_service = DashboardDataService(
            date_time_provider=DateTimeService(config),
            weather_provider=WeatherService(config),
            system_provider=SystemService(),
            github_provider=GitHubService(config),
            card_provider=KnowledgeCardService(config),
        )
        self._renderer = DashboardRenderer(
            github_username=config.github.username,
            github_organization=config.github.organization,
        )
        self._display = EPDAdapter(
            width=config.screen.width,
            height=config.screen.height,
        )
        self._dirty_tracker = DirtyRegionTracker(
            width=config.screen.width,
            height=config.screen.height,
            pixel_threshold=6,
        )
        self._ghosting_mode = config.refresh.ghosting_mode
        self._ghosting_tuning = self._build_ghosting_tuning(self._ghosting_mode)
        self._partial_streak = 0
        self._last_partial_bbox: tuple[int, int, int, int] | None = None
        self._logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        """Start infinite dashboard runtime loop."""

        self._logger.info(
            "dashboard_started screen=%sx%s partial=%ss full=%ss max_partial=%s ghosting_mode=%s hardware=%s",
            self._config.screen.width,
            self._config.screen.height,
            self._config.refresh.partial_refresh_interval_seconds,
            self._config.refresh.full_refresh_interval_seconds,
            self._config.refresh.max_partial_refreshes_before_full,
            self._ghosting_mode,
            "available" if self._display.is_hardware_available else "simulated",
        )

        # Initialize display hardware.
        use_grayscale = self._config.screen.grayscale_levels == 4
        if not self._display.initialize(grayscale=use_grayscale):
            self._logger.error("Failed to initialize display, exiting")
            return

        try:
            while True:
                decision = self._policy.decide()
                snapshot = self._data_service.collect()
                
                # Render dashboard image.
                image = self._renderer.render(snapshot)

                dirty = self._dirty_tracker.compare(image)
                dirty_ratio = dirty.changed_ratio

                if decision.mode == RefreshMode.PARTIAL and not dirty.has_changes:
                    self._logger.info(
                        "refresh skipped reason=no_visual_change tz=%s",
                        snapshot.date_time.timezone,
                    )
                    time.sleep(self._policy.sleep_seconds)
                    continue
                
                # Map refresh mode to display mode.
                display_mode = (
                    DisplayRefreshMode.FULL
                    if decision.mode == RefreshMode.FULL
                    else DisplayRefreshMode.PARTIAL
                )

                if (
                    decision.mode == RefreshMode.PARTIAL
                    and dirty.has_changes
                    and dirty_ratio >= self._ghosting_tuning.large_change_full_ratio
                ):
                    display_mode = DisplayRefreshMode.FULL

                if (
                    decision.mode == RefreshMode.PARTIAL
                    and dirty.has_changes
                    and self._should_force_full_for_ghosting(dirty.bbox, dirty_ratio)
                ):
                    display_mode = DisplayRefreshMode.FULL
                
                # Send to display.
                display_success = self._display.display(image, mode=display_mode)

                if display_mode == DisplayRefreshMode.PARTIAL and dirty.has_changes:
                    self._partial_streak += 1
                    self._last_partial_bbox = dirty.bbox
                else:
                    self._partial_streak = 0
                    self._last_partial_bbox = None
                
                self._logger.info(
                    "refresh mode=%s display_mode=%s reason=%s display=%s dirty_ratio=%.3f dirty_bbox=%s tz=%s global=%s cpu_peak=%.1f cpu_avg=%.1f mem=%.1f%% repos=%s commits=%s size=%sx%s",
                    decision.mode,
                    display_mode,
                    decision.reason,
                    "ok" if display_success else "failed",
                    dirty_ratio,
                    dirty.bbox,
                    snapshot.date_time.timezone,
                    snapshot.system.load_level,
                    snapshot.system.cpu_peak_percent,
                    snapshot.system.cpu_average_percent,
                    snapshot.system.memory_percent,
                    snapshot.github.organization_repo_count,
                    snapshot.github.organization_monthly_commit_count,
                    image.width,
                    image.height,
                )
                
                time.sleep(self._policy.sleep_seconds)
                
        except KeyboardInterrupt:
            self._logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            self._logger.error(f"Fatal error in main loop: {e}")
        finally:
            self._logger.info("Putting display to sleep...")
            self._display.sleep()

    def _should_force_full_for_ghosting(
        self,
        bbox: tuple[int, int, int, int] | None,
        dirty_ratio: float,
    ) -> bool:
        """Return True when partial refresh likely accumulates visible ghosting."""

        tuning = self._ghosting_tuning

        if self._partial_streak >= tuning.partial_streak_limit:
            return True

        if (
            dirty_ratio <= tuning.small_change_ratio
            and self._partial_streak >= tuning.small_change_streak_limit
        ):
            return True

        if bbox is None or self._last_partial_bbox is None:
            return False

        if (
            self._iou(bbox, self._last_partial_bbox) >= tuning.overlap_iou_threshold
            and self._partial_streak >= tuning.overlap_streak_limit
        ):
            return True

        return False

    @staticmethod
    def _iou(
        a: tuple[int, int, int, int],
        b: tuple[int, int, int, int],
    ) -> float:
        """Compute intersection-over-union for two bounding boxes."""

        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        if inter_area <= 0:
            return 0.0

        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = area_a + area_b - inter_area
        if union <= 0:
            return 0.0

        return inter_area / union

    @staticmethod
    def _build_ghosting_tuning(mode: str) -> GhostingTuning:
        """Build anti-ghosting thresholds from configured mode."""

        if mode == "conservative":
            return GhostingTuning(
                large_change_full_ratio=0.28,
                partial_streak_limit=6,
                small_change_ratio=0.10,
                small_change_streak_limit=3,
                overlap_iou_threshold=0.55,
                overlap_streak_limit=2,
            )

        if mode == "aggressive":
            return GhostingTuning(
                large_change_full_ratio=0.55,
                partial_streak_limit=16,
                small_change_ratio=0.05,
                small_change_streak_limit=8,
                overlap_iou_threshold=0.75,
                overlap_streak_limit=5,
            )

        return GhostingTuning(
            large_change_full_ratio=0.40,
            partial_streak_limit=10,
            small_change_ratio=0.08,
            small_change_streak_limit=5,
            overlap_iou_threshold=0.65,
            overlap_streak_limit=3,
        )
