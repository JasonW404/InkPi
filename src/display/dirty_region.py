"""Dirty-region calculation utilities for incremental e-ink refresh."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageChops


@dataclass(frozen=True)
class DirtyRegion:
    """Result of comparing current frame with previous frame."""

    bbox: tuple[int, int, int, int] | None
    changed_pixels: int
    total_pixels: int

    @property
    def has_changes(self) -> bool:
        """Whether any meaningful changes are detected."""

        return self.bbox is not None and self.changed_pixels > 0

    @property
    def changed_ratio(self) -> float:
        """Return changed-pixel ratio in [0, 1]."""

        if self.total_pixels <= 0:
            return 0.0
        return self.changed_pixels / self.total_pixels


class DirtyRegionTracker:
    """Track frame-to-frame differences for refresh optimization."""

    def __init__(self, width: int, height: int, pixel_threshold: int = 6) -> None:
        """Initialize tracker.

        Args:
            width: Frame width.
            height: Frame height.
            pixel_threshold: Ignore very small grayscale deltas (0-255).
        """

        self._total_pixels = width * height
        self._pixel_threshold = max(0, min(255, pixel_threshold))
        self._previous: Image.Image | None = None

    def compare(self, current: Image.Image) -> DirtyRegion:
        """Compare current frame with previous frame and store current.

        Args:
            current: Current rendered frame in grayscale mode.

        Returns:
            Dirty-region summary.
        """

        if self._previous is None:
            self._previous = current.copy()
            return DirtyRegion(
                bbox=(0, 0, current.width, current.height),
                changed_pixels=self._total_pixels,
                total_pixels=self._total_pixels,
            )

        diff = ImageChops.difference(self._previous, current)
        bbox = diff.getbbox()
        if bbox is None:
            self._previous = current.copy()
            return DirtyRegion(bbox=None, changed_pixels=0, total_pixels=self._total_pixels)

        binary = diff.point(lambda value: 255 if value > self._pixel_threshold else 0)
        histogram = binary.histogram()
        changed_pixels = histogram[255] if len(histogram) > 255 else 0

        self._previous = current.copy()
        return DirtyRegion(
            bbox=bbox,
            changed_pixels=changed_pixels,
            total_pixels=self._total_pixels,
        )
