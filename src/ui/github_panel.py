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
    GRAY_LIGHT,
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
    """Render GitHub contribution calendar and stats in 3-column layout."""

    def __init__(self, width: int, height: int, username: str, organization: str) -> None:
        self._width = width
        self._height = height
        self._username = username or "User"
        self._organization = organization or "Org"

    def render(self, github: GitHubMonthlyStats) -> Image.Image:
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        title_size = FONT_SIZE_TITLE + 1
        label_size = FONT_SIZE_LARGE + 1
        body_size = FONT_SIZE_NORMAL + 1
        meta_size = FONT_SIZE_SMALL + 1

        col_spacing = MARGIN
        col_padding = 6
        content_width = self._width - 2 * MARGIN - 2 * col_spacing

        # Widen center calendar column to remove left-side visual imbalance.
        min_calendar_width = 112
        preferred_calendar_width = max(120, int(content_width * 0.32))
        max_calendar_width = max(min_calendar_width, int(content_width * 0.42))
        col2_width = min(max_calendar_width, max(min_calendar_width, preferred_calendar_width))

        remaining = max(0, content_width - col2_width)
        col1_width = remaining // 2
        col3_width = remaining - col1_width

        col1_x_base = MARGIN
        col2_x_base = col1_x_base + col1_width + col_spacing
        col3_x_base = col2_x_base + col2_width + col_spacing

        col1_x = col1_x_base + col_padding
        col2_x = col2_x_base + col_padding
        col3_x = col3_x_base + col_padding

        y = MARGIN

        draw_text(
            image,
            (MARGIN, y),
            "GitHub",
            fill=GRAY_BLACK,
            font_size=title_size,
        )
        y += TITLE_LINE_HEIGHT + 5

        self._render_user_stats(
            image,
            col1_x,
            y,
            col1_width,
            github,
            label_size,
            body_size,
            meta_size,
        )

        self._render_contribution_calendar(image, col2_x, y, col2_width, github, meta_size)

        self._render_org_stats(
            image,
            col3_x,
            y,
            col3_width,
            github,
            label_size,
            body_size,
            meta_size,
        )

        separator_x1 = col1_x_base + col1_width + col_spacing // 2
        separator_x2 = col2_x_base + col2_width + col_spacing // 2
        draw_line(
            image,
            (separator_x1, y, separator_x1, self._height - MARGIN),
            fill=GRAY_LIGHT,
            width=1,
        )
        draw_line(
            image,
            (separator_x2, y, separator_x2, self._height - MARGIN),
            fill=GRAY_LIGHT,
            width=1,
        )

        return image

    def _render_user_stats(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        github: GitHubMonthlyStats,
        label_size: int,
        body_size: int,
        meta_size: int,
    ) -> None:
        name_max_width = max(40, width - 20)
        user_label, fitted_size = self._fit_label_text(
            image=image,
            text=self._username,
            max_width=name_max_width,
            preferred_size=label_size,
            min_size=max(14, meta_size),
        )
        draw_text(image, (x, y), user_label, fill=GRAY_BLACK, font_size=fitted_size)
        y += TEXT_LINE_HEIGHT + 5

        draw_line(image, (x, y, x + width - 20, y), fill=GRAY_MID, width=1)
        y += 10

        if github.contributions:
            total_commits = sum(day.commit_count for day in github.contributions)
            draw_text(
                image,
                (x, y),
                f"Commits: {total_commits}",
                fill=GRAY_BLACK,
                font_size=body_size,
            )
            y += TEXT_LINE_HEIGHT
            draw_text(
                image,
                (x, y),
                f"Days: {len(github.contributions)}",
                fill=GRAY_MID,
                font_size=meta_size,
            )
        else:
            draw_text(
                image,
                (x, y),
                "No data",
                fill=GRAY_MID,
                font_size=meta_size,
            )

    def _render_org_stats(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        github: GitHubMonthlyStats,
        label_size: int,
        body_size: int,
        meta_size: int,
    ) -> None:
        name_max_width = max(40, width - 20)
        org_label, fitted_size = self._fit_label_text(
            image=image,
            text=self._organization,
            max_width=name_max_width,
            preferred_size=label_size,
            min_size=max(14, meta_size),
        )
        draw_text(image, (x, y), org_label, fill=GRAY_BLACK, font_size=fitted_size)
        y += TEXT_LINE_HEIGHT + 5

        draw_line(image, (x, y, x + width - 20, y), fill=GRAY_MID, width=1)
        y += 10

        draw_text(
            image,
            (x, y),
            f"Repos: {github.organization_repo_count}",
            fill=GRAY_BLACK,
            font_size=body_size,
        )
        y += TEXT_LINE_HEIGHT
        draw_text(
            image,
            (x, y),
            f"Commits: {github.organization_monthly_commit_count}",
            fill=GRAY_BLACK,
            font_size=body_size,
        )
        y += TEXT_LINE_HEIGHT
        draw_text(
            image,
            (x, y),
            f"+{github.organization_additions}",
            fill=GRAY_BLACK,
            font_size=meta_size,
        )
        y += TEXT_LINE_HEIGHT
        draw_text(
            image,
            (x, y),
            f"-{github.organization_deletions}",
            fill=GRAY_MID,
            font_size=meta_size,
        )

    def _render_contribution_calendar(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        github: GitHubMonthlyStats,
        meta_size: int,
    ) -> None:
        draw_text(image, (x + 2, y), "Month", fill=GRAY_MID, font_size=meta_size)
        y += TEXT_LINE_HEIGHT + 2

        today = date.today()
        first_of_month = today.replace(day=1)
        if first_of_month.month == 12:
            next_month_first = first_of_month.replace(year=first_of_month.year + 1, month=1, day=1)
        else:
            next_month_first = first_of_month.replace(month=first_of_month.month + 1, day=1)
        last_of_month = next_month_first - timedelta(days=1)

        cols = 7
        first_weekday = first_of_month.weekday()
        total_days = last_of_month.day
        weeks = (first_weekday + total_days + cols - 1) // cols
        weeks = max(4, min(5, weeks))

        grid_padding = 4
        cell_spacing = 3
        available_width = max(1, width - grid_padding * 2)
        cell_size = max(8, min(16, (available_width - (cols - 1) * cell_spacing) // cols))
        grid_width = cols * cell_size + (cols - 1) * cell_spacing
        calendar_x = x + max(0, (width - grid_width) // 2)

        contrib_map = {item.day: item.commit_count for item in github.contributions}

        day_counter = 1 - first_weekday
        for week_idx in range(weeks):
            row_y = y + week_idx * (cell_size + cell_spacing)
            for col in range(cols):
                current_day = day_counter
                day_counter += 1
                cell_x = calendar_x + col * (cell_size + cell_spacing)

                if current_day < 1 or current_day > total_days:
                    draw_rect(
                        image,
                        (cell_x, row_y, cell_x + cell_size, row_y + cell_size),
                        fill=GRAY_WHITE,
                        outline=GRAY_LIGHT,
                        width=1,
                    )
                    continue

                current_date = first_of_month.replace(day=current_day)
                commit_count = contrib_map.get(current_date, 0)

                if commit_count == 0:
                    fill = GRAY_WHITE
                elif commit_count <= 2:
                    fill = GRAY_LIGHT
                elif commit_count <= 5:
                    fill = GRAY_MID
                else:
                    fill = GRAY_BLACK

                draw_rect(
                    image,
                    (cell_x, row_y, cell_x + cell_size, row_y + cell_size),
                    fill=fill,
                    outline=GRAY_MID,
                    width=1,
                )

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
        try:
            return cast(ImageFont.ImageFont, ImageFont.truetype("assets/fonts/MapleMono.ttf", font_size))
        except OSError:
            try:
                return cast(
                    ImageFont.ImageFont,
                    ImageFont.truetype(
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        font_size,
                    ),
                )
            except OSError:
                return cast(ImageFont.ImageFont, ImageFont.load_default())
