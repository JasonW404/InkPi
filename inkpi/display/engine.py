"""Sole owner of InkPi e-ink refresh decisions and panel state."""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Literal, Protocol

from PIL import Image, ImageChops

from inkpi.config import DisplayConfig
from inkpi.contracts import DisplayResult, DisplayStatus, FrameMetadata, utc_now_iso

RefreshAction = Literal["full", "partial"]


class DisplayBackend(Protocol):
    """Hardware operations available only inside the display module."""

    def initialize(self, grayscale: bool = True) -> bool: ...

    def display(self, image: Image.Image, action: RefreshAction) -> bool: ...

    def sleep(self) -> bool: ...


class WaveshareBackend:
    """Bridge the legacy Waveshare adapter into the isolated display service."""

    def __init__(self) -> None:
        from src.display.adapter import EPDAdapter

        self._adapter = EPDAdapter()

    def initialize(self, grayscale: bool = True) -> bool:
        return self._adapter.initialize(grayscale=grayscale)

    def display(self, image: Image.Image, action: RefreshAction) -> bool:
        from src.display.adapter import RefreshMode

        mode = RefreshMode.FULL if action == "full" else RefreshMode.PARTIAL
        return self._adapter.display(image, mode=mode)

    def sleep(self) -> bool:
        return self._adapter.sleep()


@dataclass
class _FrameJob:
    image: Image.Image
    metadata: FrameMetadata
    done: threading.Event
    result: DisplayResult | None = None


class DisplayEngine:
    """Serialize frame submissions and apply a longevity-first refresh policy."""

    def __init__(self, backend: DisplayBackend, config: DisplayConfig) -> None:
        self._backend = backend
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        self._queue: queue.Queue[_FrameJob] = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._running = False
        self._worker: threading.Thread | None = None
        self._initialized = False
        self._previous: Image.Image | None = None
        self._active_page_id: str | None = None
        self._partial_streak = 0
        self._full_refreshes = 0
        self._partial_refreshes = 0
        self._skipped_refreshes = 0
        self._consecutive_failures = 0
        self._last_action: str | None = None
        self._last_reason: str | None = None
        self._last_refresh_at: str | None = None

    def start(self) -> None:
        """Initialize hardware and start the serialized display worker."""

        if self._running:
            return
        self._initialized = self._backend.initialize(grayscale=True)
        if not self._initialized:
            raise RuntimeError("display initialization failed")
        self._running = True
        self._worker = threading.Thread(target=self._run, name="inkpi-display", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        """Stop the worker and put the panel into deep sleep."""

        self._running = False
        if self._worker:
            self._worker.join(timeout=10)
        if self._initialized:
            self._backend.sleep()
        self._initialized = False

    def submit(self, image: Image.Image, metadata: FrameMetadata, timeout: float = 30) -> DisplayResult:
        """Submit a complete logical frame, replacing obsolete pending work."""

        if image.size != (800, 480):
            return DisplayResult(False, "failed", "invalid_frame_size", error_code="invalid_frame")
        job = _FrameJob(image=image.convert("L").copy(), metadata=metadata, done=threading.Event())
        with self._lock:
            if self._queue.full():
                replaced = self._queue.get_nowait()
                if replaced.metadata.urgency == "immediate" and metadata.urgency == "normal":
                    self._queue.put_nowait(replaced)
                    return DisplayResult(True, "replaced", "dropped_behind_immediate_frame")
                replaced.result = DisplayResult(True, "replaced", "superseded_by_newer_frame")
                replaced.done.set()
            self._queue.put_nowait(job)
        if not job.done.wait(timeout):
            return DisplayResult(False, "failed", "display_timeout", error_code="timeout")
        return job.result or DisplayResult(False, "failed", "missing_display_result", error_code="internal")

    def status(self) -> DisplayStatus:
        """Return current panel telemetry."""

        return DisplayStatus(
            healthy=self._initialized and self._consecutive_failures < 3,
            initialized=self._initialized,
            active_page_id=self._active_page_id,
            last_action=self._last_action,
            last_reason=self._last_reason,
            last_refresh_at=self._last_refresh_at,
            full_refreshes=self._full_refreshes,
            partial_refreshes=self._partial_refreshes,
            skipped_refreshes=self._skipped_refreshes,
            consecutive_failures=self._consecutive_failures,
            pending_frames=self._queue.qsize(),
        )

    def _run(self) -> None:
        while self._running:
            try:
                job = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            job.result = self._process(job.image, job.metadata)
            job.done.set()

    def _process(self, image: Image.Image, metadata: FrameMetadata) -> DisplayResult:
        started = time.monotonic()
        action, reason = self._decide(image, metadata)
        if action == "skipped":
            self._skipped_refreshes += 1
            self._record(action, reason)
            return DisplayResult(True, "skipped", reason)

        assert action in {"full", "partial"}
        output = image if action == "full" else self._monochrome(image)
        success = self._backend.display(output, action)
        duration_ms = (time.monotonic() - started) * 1000
        if success:
            self._previous = image.copy()
            self._active_page_id = metadata.page_id
            self._consecutive_failures = 0
            if action == "full":
                self._full_refreshes += 1
                self._partial_streak = 0
            else:
                self._partial_refreshes += 1
                self._partial_streak += 1
            self._record(action, reason)
            return DisplayResult(True, action, reason, duration_ms)

        self._consecutive_failures += 1
        self._previous = None
        self._partial_streak = 0
        self._record("failed", "backend_refresh_failed")
        if self._consecutive_failures >= 2:
            self._initialized = self._backend.initialize(grayscale=True)
        return DisplayResult(
            False,
            "failed",
            "backend_refresh_failed",
            duration_ms,
            error_code="display_failure",
        )

    def _decide(self, image: Image.Image, metadata: FrameMetadata) -> tuple[str, str]:
        if self._previous is None:
            return "full", "startup_or_recovery"
        if metadata.page_id != self._active_page_id:
            return "full", "page_changed"

        changed_ratio, grayscale_changed = self._difference(image)
        if changed_ratio < self._config.meaningful_change_ratio:
            return "skipped", "no_meaningful_visual_change"
        if grayscale_changed:
            return "full", "grayscale_change"
        if self._partial_streak >= self._config.max_partial_refreshes:
            return "full", "partial_refresh_limit"
        if changed_ratio > self._config.partial_change_ratio:
            return "full", "large_visual_change"
        return "partial", "small_monochrome_same_page_change"

    def _difference(self, image: Image.Image) -> tuple[float, bool]:
        assert self._previous is not None
        previous = self._previous.convert("L")
        current = image.convert("L")
        diff = ImageChops.difference(previous, current)
        histogram = diff.point(lambda value: 255 if value > 6 else 0).histogram()
        changed = histogram[255] if len(histogram) > 255 else 0
        changed_ratio = changed / (image.width * image.height)
        grayscale_changed = self._monochrome(previous).tobytes() == self._monochrome(current).tobytes() and changed > 0
        return changed_ratio, grayscale_changed

    @staticmethod
    def _monochrome(image: Image.Image) -> Image.Image:
        return image.convert("L").point(lambda value: 255 if value >= 150 else 0, mode="1")

    def _record(self, action: str, reason: str) -> None:
        self._last_action = action
        self._last_reason = reason
        self._last_refresh_at = utc_now_iso()
        self._logger.info("display action=%s reason=%s page=%s", action, reason, self._active_page_id)
