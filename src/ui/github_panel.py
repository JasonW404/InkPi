"""GitHub statistics panel renderer."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, cast

from PIL import Image
from PIL import ImageDraw, ImageFont

from src.ui.constants import (
    FONT_SIZE_LARGE,
    FONT_SIZE_NORMAL,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    GRAY_BLACK,
    GRAY_MID,
    GRAY_WHITE,
    MARGIN,
    TEXT_LINE_HEIGHT,
    TITLE_LINE_HEIGHT,
)
from src.ui.drawing import draw_line, draw_rect, draw_text

if TYPE_CHECKING:
    from src.domain.models import GitHubMonthlyStats


class GitHubPanel:
    """Render compact GitHub stats and 21-day contribution calendar."""

    def __init__(self, width: int, height: int, username: str, organization: str) -> None:
        self._width = width
        self._height = height
        self._username = username or "User"
        self._organization = organization or "Org"

    def render(self, github: GitHubMonthlyStats) -> Image.Image:
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        title_size = FONT_SIZE_TITLE
        label_size = FONT_SIZE_LARGE
        body_size = FONT_SIZE_NORMAL
        meta_size = FONT_SIZE_SMALL

        content_x = MARGIN
        content_width = self._width - 2 * MARGIN
        y = MARGIN + 1

        draw_text(
            image,
            (content_x, y),
            "GitHub",
            fill=GRAY_BLACK,
            font_size=title_size,
        )
        y += TITLE_LINE_HEIGHT + 10

        user_commits = sum(day.commit_count for day in github.contributions)
        user_code_lines = max(0, github.user_monthly_code_lines)
        org_code_lines = max(0, github.organization_monthly_code_lines)

        y = self._render_summary_row(
            image=image,
            x=content_x,
            y=y,
            width=content_width,
            name=self._username,
            commit_count=user_commits,
            code_lines=user_code_lines,
            name_size=label_size,
            value_size=body_size,
            meta_size=meta_size,
        )
        y = self._render_summary_row(
            image=image,
            x=content_x,
            y=y,
            width=content_width,
            name=self._organization,
            commit_count=github.organization_monthly_commit_count,
            code_lines=org_code_lines,
            name_size=label_size,
            value_size=body_size,
            meta_size=meta_size,
        )

        draw_line(
            image,
            (content_x, y - 2, content_x + content_width, y - 2),
            fill=GRAY_MID,
            width=1,
        )

        self._render_contribution_calendar(
            image=image,
            x=content_x,
            y=y + 20,
            width=content_width,
            github=github,
            meta_size=meta_size,
        )

        return image

    def _render_summary_row(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        name: str,
        commit_count: int,
        code_lines: int,
        name_size: int,
        value_size: int,
        meta_size: int,
    ) -> int:
        """Render one compact summary row (name + stats on same line)."""

        row_height = TEXT_LINE_HEIGHT + 8
        name_max_width = max(200, int(width * 0.32))
        name_label, fitted_size = self._fit_label_text(
            image=image,
            text=name,
            max_width=name_max_width,
            preferred_size=name_size,
            min_size=max(14, meta_size),
        )
        draw_text(image, (x, y), name_label, fill=GRAY_BLACK, font_size=fitted_size)

        stats_y = y
        stats_x = x + name_max_width + 20
        commit_x = stats_x
        self._draw_fixed_width_stat(
            image=image,
            x=commit_x,
            y=stats_y,
            label="COMMITS",
            value=max(0, commit_count),
            value_box_width=48,
            font_size=value_size,
        )

        code_x = commit_x + 160
        self._draw_fixed_width_stat(
            image=image,
            x=code_x,
            y=stats_y,
            label="LINES",
            value=max(0, code_lines),
            value_box_width=60,
            font_size=value_size,
        )

        draw_line(image, (x, y + row_height - 3, x + width, y + row_height - 3), fill=GRAY_MID, width=1)
        return y + row_height

    def _render_contribution_calendar(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        github: GitHubMonthlyStats,
        meta_size: int,
    ) -> None:
        draw = ImageDraw.Draw(image)

        cols = 21
        cell_spacing = 5
        grid_padding = 4
        available_width = max(1, width - grid_padding * 2)
        cell_size = max(1, (available_width - (cols - 1) * cell_spacing) // cols)
        grid_width = cols * cell_size + (cols - 1) * cell_spacing
        calendar_x = x + max(0, (width - grid_width) // 2)

        today = date.today()
        current_week_start = today - timedelta(days=(today.weekday() + 1) % 7)
        start_date = current_week_start - timedelta(days=14)

        contrib_map = {item.day: item.commit_count for item in github.contributions}

        row_y = y
        for col in range(cols):
            current_date = start_date + timedelta(days=col)
            commit_count = contrib_map.get(current_date, 0)
            fill = self._resolve_contribution_fill(commit_count)
            cell_x = calendar_x + col * (cell_size + cell_spacing)

            draw_rect(
                image,
                (cell_x, row_y, cell_x + cell_size, row_y + cell_size),
                fill=fill,
                outline=GRAY_MID,
                width=1,
            )

            day_text = str(current_date.day)
            day_font_size = 16
            font = self._load_font(day_font_size)
            text_box = draw.textbbox((0, 0), day_text, font=font)
            text_w = text_box[2] - text_box[0]
            text_h = text_box[3] - text_box[1]
            text_x = int(cell_x + max(0, (cell_size - text_w) // 2))
            text_y = int(row_y + cell_size + 3 + max(0, (day_font_size - text_h) // 2))
            draw_text(image, (text_x, text_y), day_text, fill=GRAY_BLACK, font_size=day_font_size)

    def _draw_fixed_width_stat(
        self,
        image: Image.Image,
        x: int,
        y: int,
        label: str,
        value: int,
        value_box_width: int,
        font_size: int,
    ) -> None:
        """Draw label + fixed-width centered numeric value (no zero padding)."""

        draw = ImageDraw.Draw(image)
        label_text = f"{label}"
        draw_text(image, (x, y), label_text, fill=GRAY_BLACK, font_size=font_size)

        label_font = self._load_font(font_size)
        label_box = draw.textbbox((0, 0), label_text, font=label_font)
        label_width = label_box[2] - label_box[0]

        value_text = str(max(0, value))
        value_font = self._load_font(font_size)
        value_box = draw.textbbox((0, 0), value_text, font=value_font)
        value_width = value_box[2] - value_box[0]

        value_x = int(x + label_width + 10 + max(0, (value_box_width - value_width) // 2))
        draw_text(image, (value_x, y), value_text, fill=GRAY_BLACK, font_size=font_size)

    @staticmethod
    def _resolve_contribution_fill(commit_count: int) -> int:
        if commit_count == 0:
            return GRAY_WHITE
        if commit_count <= 2:
            return 140
        if commit_count <= 5:
            return GRAY_MID
        return GRAY_BLACK

    def _fit_label_text(
        self,
        image: Image.Image,
        text: str,
        max_width: int,
        preferred_size: int,
        min_size: int,
    ) -> tuple[str, int]:
        draw = ImageDraw.Draw(image)
        text_value = text.strip() or "-"

        for size in range(preferred_size, min_size - 1, -1):
            font = self._load_font(size)
            text_width = draw.textbbox((0, 0), text_value, font=font)[2]
            if text_width <= max_width:
                return text_value, size

        size = min_size
        font = self._load_font(size)
        if draw.textbbox((0, 0), text_value, font=font)[2] <= max_width:
            return text_value, size

        shortened = text_value
        while len(shortened) > 1:
            shortened = shortened[:-1]
            candidate = shortened + "..."
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                return candidate, size
        return "...", size

    @staticmethod
    def _load_font(font_size: int) -> ImageFont.ImageFont:
        """Load the primary UI font with fallback to default font."""
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
