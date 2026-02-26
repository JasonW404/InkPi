"""Lifecycle screen renderer for startup and shutdown states."""

from __future__ import annotations

from PIL import Image

from src.ui.constants import FONT_SIZE_NORMAL, FONT_SIZE_TITLE, GRAY_BLACK, GRAY_LIGHT, GRAY_MID, GRAY_WHITE
from src.ui.drawing import draw_rect, draw_text


class LifecycleScreenRenderer:
    """Render full-screen lifecycle states for boot and shutdown."""

    def __init__(self, width: int, height: int) -> None:
        """Initialize renderer for fixed display dimensions.

        Args:
            width: Display width in pixels.
            height: Display height in pixels.
        """

        self._width = width
        self._height = height

    def render_startup(self) -> Image.Image:
        """Render startup screen shown while first snapshot is loading."""

        return self._render(
            title="eInk Dashboard",
            subtitle="Starting up...",
            detail="Preparing first data snapshot",
        )

    def render_shutdown(self) -> Image.Image:
        """Render shutdown screen shown before entering deep sleep."""

        return self._render(
            title="eInk Dashboard",
            subtitle="Shutting down...",
            detail="Display will keep this screen in sleep mode",
        )

    def _render(self, title: str, subtitle: str, detail: str) -> Image.Image:
        """Render a centered lifecycle screen with consistent grayscale styling."""

        image = Image.new("L", (self._width, self._height), GRAY_WHITE)
        frame_padding = 28
        draw_rect(
            image,
            (
                frame_padding,
                frame_padding,
                self._width - frame_padding,
                self._height - frame_padding,
            ),
            fill=None,
            outline=GRAY_LIGHT,
            width=2,
        )

        text_left = 72
        center_y = self._height // 2
        draw_text(
            image,
            (text_left, center_y - 68),
            title,
            fill=GRAY_BLACK,
            font_size=FONT_SIZE_TITLE,
            font_weight="bold",
        )
        draw_text(
            image,
            (text_left, center_y - 22),
            subtitle,
            fill=GRAY_BLACK,
            font_size=FONT_SIZE_TITLE,
            font_weight="semibold",
        )
        draw_text(
            image,
            (text_left, center_y + 28),
            detail,
            fill=GRAY_MID,
            font_size=FONT_SIZE_NORMAL,
            font_weight="regular",
        )

        return image