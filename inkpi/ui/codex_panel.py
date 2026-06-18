"""Codex usage panel renderer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from typing import cast

from PIL import Image, ImageDraw, ImageFont

from inkpi.ui.constants import (
    FONT_SIZE_LARGE,
    FONT_SIZE_NORMAL,
    FONT_SIZE_SMALL,
    GRAY_BLACK,
    GRAY_LIGHT,
    GRAY_MID,
    GRAY_WHITE,
    MARGIN,
)
from inkpi.ui.drawing import draw_line, draw_rect, draw_text, truncate_text

if TYPE_CHECKING:
    from inkpi.domain.models import CodexUsageInfo


class CodexPanel:
    """Render compact Codex usage with stacked progress bars."""

    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    def render(self, codex: CodexUsageInfo) -> Image.Image:
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        content_x = MARGIN
        content_width = self._width - 2 * MARGIN

        draw = ImageDraw.Draw(image)
        normal_font = self._load_font(FONT_SIZE_NORMAL)
        small_font = self._load_font(FONT_SIZE_SMALL)

        y = 8
        draw_text(image, (content_x, y), "CODEX USAGE", fill=GRAY_BLACK, font_size=FONT_SIZE_LARGE, font_weight="bold")

        plan_text = codex.plan.upper()
        plan_w = draw.textbbox((0, 0), plan_text, font=small_font)[2]
        status_text = "LIVE" if codex.ok else "STALE"
        status_w = draw.textbbox((0, 0), status_text, font=small_font)[2]

        status_x = content_x + content_width - status_w
        plan_x = status_x - plan_w - 12
        draw_text(image, (int(plan_x), y + 4), plan_text, fill=GRAY_BLACK, font_size=FONT_SIZE_SMALL)
        draw_text(image, (int(status_x), y + 4), status_text, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)

        y = 40

        if not codex.ok or not codex.windows:
            draw_text(image, (content_x, y), "UNAVAILABLE", fill=GRAY_BLACK, font_size=FONT_SIZE_LARGE, font_weight="bold")
            error_msg = truncate_text(codex.error or "No quota windows returned.", 60)
            draw_text(image, (content_x, y + 28), error_msg, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)
            return image

        column_gap = 20
        column_width = (content_width - column_gap) // 2
        bar_height = 16
        bar_width = column_width - 10

        windows = codex.windows[:2]

        for index, window in enumerate(windows):
            col_x = content_x + index * (column_width + column_gap)
            remaining = max(0, min(100, window.remaining_percent))

            draw_text(image, (col_x, y), window.label, fill=GRAY_MID, font_size=FONT_SIZE_SMALL, font_weight="semibold")

            percent_text = f"{int(round(remaining)):>3}%"
            percent_w = draw.textbbox((0, 0), percent_text, font=normal_font)[2]
            percent_x = col_x + column_width - percent_w
            draw_text(
                image,
                (int(percent_x), y - 2),
                percent_text,
                fill=GRAY_BLACK,
                font_size=FONT_SIZE_NORMAL,
                font_weight="bold",
            )

            bar_y = y + 22
            draw_rect(
                image,
                (col_x, bar_y, col_x + bar_width, bar_y + bar_height),
                fill=None,
                outline=GRAY_MID,
                width=1,
            )
            fill_width = int(bar_width * remaining / 100)
            if fill_width > 0:
                draw_rect(
                    image,
                    (col_x, bar_y, col_x + fill_width, bar_y + bar_height),
                    fill=GRAY_BLACK,
                )

            countdown = _countdown(window.resets_at)
            draw_text(
                image,
                (col_x, bar_y + bar_height + 4),
                f"RESET {countdown:>8}",
                fill=GRAY_MID,
                font_size=FONT_SIZE_SMALL,
            )

        if len(windows) > 1:
            sep_x = content_x + column_width + column_gap // 2
            draw_line(image, (sep_x, y, sep_x, self._height - 6), fill=GRAY_LIGHT, width=1)

        return image

    @staticmethod
    def _load_font(font_size: int) -> ImageFont.ImageFont:
        candidates = [
            "assets/fonts/MapleMono-CN-Regular.ttf",
            "assets/fonts/MapleMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            try:
                return cast(ImageFont.ImageFont, ImageFont.truetype(path, font_size))
            except OSError:
                continue
        return cast(ImageFont.ImageFont, ImageFont.load_default())


def _countdown(value: str | None) -> str:
    if not value:
        return "--"
    try:
        reset = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "--"
    seconds = max(0, int((reset - datetime.now(UTC)).total_seconds()))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    return f"{days}D {hours:02}:{minutes:02}" if days else f"{hours:02}:{minutes:02}"
