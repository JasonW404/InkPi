"""Anti-ghosting heuristics for deciding full refresh escalation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GhostingTuning:
    """Anti-ghosting thresholds controlled by ghosting mode."""

    large_change_full_ratio: float
    partial_streak_limit: int
    small_change_ratio: float
    small_change_streak_limit: int
    overlap_iou_threshold: float
    overlap_streak_limit: int


class GhostingGuard:
    """Track partial refresh history and predict ghosting risk."""

    def __init__(self, mode: str) -> None:
        """Initialize guard with configured mode.

        Args:
            mode: Ghosting mode from configuration.
        """

        self._mode = mode
        self._tuning = self._build_tuning(mode)
        self._partial_streak = 0
        self._last_partial_bbox: tuple[int, int, int, int] | None = None

    @property
    def mode(self) -> str:
        """Return configured ghosting mode."""

        return self._mode

    def should_upgrade_for_large_change(self, dirty_ratio: float) -> bool:
        """Return True when change area is too large for stable partial update."""

        return dirty_ratio >= self._tuning.large_change_full_ratio

    def should_force_full(
        self,
        bbox: tuple[int, int, int, int] | None,
        dirty_ratio: float,
    ) -> bool:
        """Return True when partial refresh likely accumulates visible ghosting."""

        tuning = self._tuning

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

    def register_refresh(
        self,
        *,
        was_partial: bool,
        has_changes: bool,
        bbox: tuple[int, int, int, int] | None,
    ) -> None:
        """Record outcome of this frame to update streak state."""

        if was_partial and has_changes:
            self._partial_streak += 1
            self._last_partial_bbox = bbox
            return

        self._partial_streak = 0
        self._last_partial_bbox = None

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
    def _build_tuning(mode: str) -> GhostingTuning:
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
