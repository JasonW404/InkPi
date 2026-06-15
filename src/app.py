"""Application runtime orchestration for dashboard refresh cycles."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
import logging
import signal
import time
from types import FrameType
from typing import TYPE_CHECKING, Any, Callable, TypeAlias

from src.bootstrap import build_runtime_components
from src.config import AppConfig
from src.display.adapter import RefreshMode as DisplayRefreshMode
from src.runtime.ghosting import GhostingGuard
from src.runtime.refresh_policy import RefreshMode, RefreshPolicy

if TYPE_CHECKING:
    from src.domain.models import DashboardSnapshot


SignalHandler: TypeAlias = Callable[[int, FrameType | None], Any] | int | signal.Handlers | None


class DashboardApplication:
    """Main application loop that collects data and schedules refresh."""

    def __init__(self, config: AppConfig) -> None:
        """Create runtime dependencies.

        Args:
            config: Application configuration.
        """

        self._config = config
        self._policy = RefreshPolicy(config)
        runtime = build_runtime_components(config)
        self._data_service = runtime.data_service
        self._renderer = runtime.renderer
        self._lifecycle_renderer = runtime.lifecycle_renderer
        self._display = runtime.display
        self._dirty_tracker = runtime.dirty_tracker
        self._ghosting_guard = GhostingGuard(config.refresh.ghosting_mode)
        self._running = True
        self._received_signal: int | None = None
        self._previous_signal_handlers: dict[int, SignalHandler] = {}
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
            self._ghosting_guard.mode,
            "available" if self._display.is_hardware_available else "simulated",
        )

        # Initialize display hardware.
        use_grayscale = self._config.screen.grayscale_levels == 4
        if not self._display.initialize(grayscale=use_grayscale):
            self._logger.error("Failed to initialize display, exiting")
            return

        self._install_signal_handlers()

        try:
            self._show_startup_screen()
            initial_snapshot = self._collect_initial_snapshot()
            if initial_snapshot is None:
                self._logger.info("startup_aborted reason=termination_requested")
                return

            initial_image = self._renderer.render(initial_snapshot)
            initial_display_success = self._display.display(
                initial_image,
                mode=DisplayRefreshMode.FULL,
            )
            self._dirty_tracker.compare(initial_image)
            self._policy.mark_external_full_refresh()

            self._logger.info(
                "initial_refresh display=%s tz=%s global=%s cpu_peak=%.1f cpu_avg=%.1f mem=%.1f%% repos=%s commits=%s size=%sx%s",
                "ok" if initial_display_success else "failed",
                initial_snapshot.date_time.timezone,
                initial_snapshot.system.load_level,
                initial_snapshot.system.cpu_peak_percent,
                initial_snapshot.system.cpu_average_percent,
                initial_snapshot.system.memory_percent,
                initial_snapshot.github.organization_repo_count,
                initial_snapshot.github.organization_monthly_commit_count,
                initial_image.width,
                initial_image.height,
            )

            while self._running:
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
                    self._sleep_until_next_cycle(self._policy.sleep_seconds)
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
                    and self._ghosting_guard.should_upgrade_for_large_change(dirty_ratio)
                ):
                    display_mode = DisplayRefreshMode.FULL

                if (
                    decision.mode == RefreshMode.PARTIAL
                    and dirty.has_changes
                    and self._ghosting_guard.should_force_full(dirty.bbox, dirty_ratio)
                ):
                    display_mode = DisplayRefreshMode.FULL
                
                # Send to display.
                display_success = self._display.display(image, mode=display_mode)
                self._ghosting_guard.register_refresh(
                    was_partial=display_mode == DisplayRefreshMode.PARTIAL,
                    has_changes=dirty.has_changes,
                    bbox=dirty.bbox,
                )
                
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

                self._sleep_until_next_cycle(self._policy.sleep_seconds)
                
        except KeyboardInterrupt:
            self._running = False
            self._logger.info("Received interrupt signal, shutting down...")
        except Exception:
            self._logger.exception("fatal_error_in_main_loop")
        finally:
            self._restore_signal_handlers()
            self._shutdown_display()

    def _install_signal_handlers(self) -> None:
        """Install SIGINT/SIGTERM handlers for graceful shutdown screen rendering."""

        handled_signals = [signal.SIGINT]
        if hasattr(signal, "SIGTERM"):
            handled_signals.append(signal.SIGTERM)

        for sig in handled_signals:
            self._previous_signal_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self._handle_termination_signal)

    def _restore_signal_handlers(self) -> None:
        """Restore signal handlers active before application startup."""

        for sig, previous_handler in self._previous_signal_handlers.items():
            signal.signal(sig, previous_handler)
        self._previous_signal_handlers.clear()

    def _handle_termination_signal(self, signum: int, _frame: FrameType | None) -> None:
        """Signal callback that requests loop termination.

        Args:
            signum: Received signal number.
            _frame: Current frame object supplied by signal module.
        """

        if not self._running:
            return

        self._running = False
        self._received_signal = signum
        self._logger.info("termination_signal_received signal=%s", signum)

    def _show_startup_screen(self) -> None:
        """Render and display startup screen before first dashboard snapshot."""

        startup_image = self._lifecycle_renderer.render_startup()
        startup_ok = self._display.display(startup_image, mode=DisplayRefreshMode.FULL)
        self._logger.info("startup_screen_rendered display=%s", "ok" if startup_ok else "failed")

    def _collect_initial_snapshot(self) -> DashboardSnapshot | None:
        """Collect first dashboard snapshot in background while startup screen is visible."""

        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="initial-data") as executor:
            future = executor.submit(self._data_service.collect)
            while self._running:
                try:
                    return future.result(timeout=0.2)
                except TimeoutError:
                    continue

            future.cancel()
            return None

    def _sleep_until_next_cycle(self, seconds: int) -> None:
        """Sleep in small slices to react quickly to termination signals."""

        remaining = max(0.0, float(seconds))
        while self._running and remaining > 0:
            interval = min(0.2, remaining)
            time.sleep(interval)
            remaining -= interval

    def _shutdown_display(self) -> None:
        """Render shutdown screen, force full refresh, then put display to sleep."""

        if not self._display.is_initialized:
            return

        self._logger.info("shutdown_begin signal=%s", self._received_signal)

        shutdown_image = self._lifecycle_renderer.render_shutdown()
        stage_ok = self._display.display(shutdown_image, mode=DisplayRefreshMode.PARTIAL)
        self._logger.info(
            "shutdown_screen_staged display=%s",
            "ok" if stage_ok else "failed",
        )

        shutdown_ok = self._display.display(shutdown_image, mode=DisplayRefreshMode.FULL)

        self._logger.info(
            "shutdown_screen_rendered display=%s entering_sleep=true",
            "ok" if shutdown_ok else "failed",
        )
        self._display.sleep()
