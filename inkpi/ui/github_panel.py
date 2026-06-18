"""GitHub statistics panel renderer."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, cast

from PIL import Image
from PIL import ImageDraw, ImageFont

from inkpi.ui.constants import (
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
from inkpi.ui.drawing import draw_rect, draw_text

if TYPE_CHECKING:
    from inkpi.domain.models import GitHubMonthlyStats


class GitHubPanel:
    """Render compact GitHub stats and current-month contribution calendar."""

    def __init__(self, width: int, height: int, username: str, organization: str) -> None:
        self._width = width
        self._height = height
        self._username = username or "User"
        self._organization = organization or "Org"

    def render(self, github: GitHubMonthlyStats) -> Image.Image:
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        title_size = FONT_SIZE_LARGE
        content_x = MARGIN
        y = MARGIN + 1

        draw_text(
            image,
            (content_x, y),
            "GITHUB CONTRIBUTIONS",
            fill=GRAY_BLACK,
            font_size=title_size,
            font_weight="bold",
        )
        y += TITLE_LINE_HEIGHT - 2

        user_commits = max(0, github.user_monthly_commit_count)
        user_code_lines = max(0, github.user_monthly_code_lines)
        org_commits = max(0, github.organization_user_monthly_commit_count)
        org_code_lines = max(0, github.organization_user_monthly_code_lines)

        # Tunable layout coordinates, all relative to this GitHub panel.
        stats_x = content_x + 48
        stats_y = y + 20
        stats_width = 480

        calendar_width = 188
        calendar_height = self._height - y - MARGIN
        calendar_x = self._width - MARGIN - calendar_width
        calendar_y = MARGIN

        self._render_stats_dashboard(
            image=image,
            x=stats_x,
            y=stats_y,
            width=stats_width,
            user_commits=user_commits,
            user_code_lines=user_code_lines,
            org_commits=org_commits,
            org_code_lines=org_code_lines,
            font_size=FONT_SIZE_TITLE,
        )

        self._render_contribution_calendar(
            image=image,
            x=calendar_x,
            y=calendar_y,
            width=calendar_width,
            height=calendar_height,
            github=github,
        )

        return image

    def _render_stats_dashboard(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        user_commits: int,
        user_code_lines: int,
        org_commits: int,
        org_code_lines: int,
        font_size: int,
    ) -> None:
        """Render the numeric stats column."""

        gap = 80
        column_width = max(138, (width - gap) // 2)
        total_width = column_width * 2 + gap
        start_x = x + max(0, (width - total_width) // 2)
        start_y = y
        self._render_metric_group(
            image=image,
            x=start_x,
            y=start_y,
            width=column_width,
            text=self._username,
            commits=user_commits,
            lines=user_code_lines,
            font_size=font_size,
        )
        self._render_metric_group(
            image=image,
            x=start_x + column_width + gap,
            y=start_y,
            width=column_width,
            text=self._organization,
            commits=org_commits,
            lines=org_code_lines,
            font_size=font_size,
        )

    def _render_metric_group(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        text: str,
        commits: int,
        lines: int,
        font_size: int,
    ) -> None:
        group_label, label_size = self._fit_label_text(
            image=image,
            text=text,
            max_width=width,
            preferred_size=FONT_SIZE_LARGE,
            min_size=FONT_SIZE_SMALL,
            font_weight="semibold",
        )
        draw = ImageDraw.Draw(image)
        label_font = self._load_font(label_size, font_weight="semibold")
        label_width = draw.textbbox((0, 0), group_label, font=label_font)[2]
        label_x = x + max(0, (width - label_width) // 2)
        draw_text(image, (int(label_x), y), group_label, fill=GRAY_BLACK, font_size=label_size, font_weight="semibold")
        metric_y = y + TEXT_LINE_HEIGHT + 12
        metric_gap = 80
        metric_total_width = max(1, width - metric_gap)
        commits_width = max(1, metric_total_width * 2 // 5)
        lines_width = max(1, metric_total_width - commits_width)
        self._render_stacked_metric(image, x, metric_y, commits_width, "COMMITS", commits, 5, font_size)
        self._render_stacked_metric(
            image,
            x + commits_width + metric_gap,
            metric_y,
            lines_width,
            "LINES",
            lines,
            8,
            font_size,
        )

    def _render_stacked_metric(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        label: str,
        value: int,
        digits: int,
        font_size: int,
    ) -> int:
        draw = ImageDraw.Draw(image)
        value_text = str(max(0, value))
        label_font = self._load_font(FONT_SIZE_SMALL)
        value_font = self._load_font(font_size, font_weight="bold")
        label_width = draw.textbbox((0, 0), label, font=label_font)[2]
        value_width = draw.textbbox((0, 0), value_text, font=value_font)[2]

        value_x = x + max(0, (width - value_width) // 2)
        label_x = x + max(0, (width - label_width) // 2)
        draw_text(image, (int(value_x), y), value_text, fill=GRAY_BLACK, font_size=font_size, font_weight="bold")
        draw_text(image, (int(label_x), y + 32), label, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)
        return y + 56

    def _render_contribution_calendar(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        github: GitHubMonthlyStats,
    ) -> None:
        today = date.today()
        first_day = today.replace(day=1)
        if first_day.month == 12:
            next_month = first_day.replace(year=first_day.year + 1, month=1)
        else:
            next_month = first_day.replace(month=first_day.month + 1)
        last_day = next_month - timedelta(days=1)

        start_date = first_day - timedelta(days=first_day.weekday())
        end_date = last_day + timedelta(days=6 - last_day.weekday())
        days = (end_date - start_date).days + 1
        cols = 7
        display_rows = max(1, days // 7)
        header_height = 16
        cell_spacing = 5
        row_spacing = 3
        dot_space = 5
        available_width = max(1, width)
        available_height = max(1, height)
        cell_from_width = (available_width - (cols - 1) * cell_spacing) // cols
        cell_from_height = (
            available_height - header_height - (display_rows - 1) * row_spacing - dot_space
        ) // display_rows
        cell_size = max(8, min(cell_from_width, cell_from_height, 30))
        grid_width = cols * cell_size + (cols - 1) * cell_spacing
        calendar_x = x + max(0, width - grid_width)
        weekdays = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        draw = ImageDraw.Draw(image)
        weekday_font = self._load_font(FONT_SIZE_SMALL)
        for col, weekday in enumerate(weekdays):
            label_width = draw.textbbox((0, 0), weekday, font=weekday_font)[2]
            label_x = calendar_x + col * (cell_size + cell_spacing) + max(0, (cell_size - label_width) // 2)
            draw_text(image, (int(label_x), y), weekday, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)

        grid_y = y + header_height + row_spacing

        contrib_map = {item.day: item.commit_count for item in github.contributions}

        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            row = day_offset // cols
            col = day_offset % cols
            in_month = current_date.month == today.month
            if not in_month:
                continue
            commit_count = contrib_map.get(current_date, 0)
            fill = self._resolve_contribution_fill(commit_count)
            cell_x = calendar_x + col * (cell_size + cell_spacing)
            cell_y = grid_y + row * (cell_size + row_spacing)

            draw_rect(
                image,
                (cell_x, cell_y, cell_x + cell_size, cell_y + cell_size),
                fill=fill,
                outline=GRAY_MID,
                width=1,
            )

            if current_date == today:
                dot_size = max(3, min(5, cell_size // 6))
                dot_x = cell_x + (cell_size - dot_size) // 2
                dot_y = cell_y + cell_size + 3
                draw = ImageDraw.Draw(image)
                draw.ellipse(
                    (dot_x, dot_y, dot_x + dot_size, dot_y + dot_size),
                    fill=GRAY_BLACK,
                    outline=GRAY_BLACK,
                )

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
        font_weight: str = "regular",
    ) -> tuple[str, int]:
        draw = ImageDraw.Draw(image)
        text_value = text.strip() or "-"

        for size in range(preferred_size, min_size - 1, -1):
            font = self._load_font(size, font_weight=font_weight)
            text_width = draw.textbbox((0, 0), text_value, font=font)[2]
            if text_width <= max_width:
                return text_value, size

        size = min_size
        font = self._load_font(size, font_weight=font_weight)
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
    def _load_font(font_size: int, font_weight: str = "regular") -> ImageFont.ImageFont:
        """Load the primary UI font with fallback to default font."""
        weight_candidates = {
            "regular": ["MapleMono-CN-Regular.ttf", "MapleMono.ttf"],
            "semibold": [
                "MapleMono-CN-SemiBold.ttf",
                "MapleMono-CN-Medium.ttf",
                "MapleMono-CN-Regular.ttf",
                "MapleMono.ttf",
            ],
            "bold": [
                "MapleMono-CN-Bold.ttf",
                "MapleMono-CN-SemiBold.ttf",
                "MapleMono-CN-Medium.ttf",
                "MapleMono-CN-Regular.ttf",
                "MapleMono.ttf",
            ],
        }
        candidates = [
            f"assets/fonts/{filename}"
            for filename in weight_candidates.get(font_weight, weight_candidates["regular"])
        ]
        candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        for path in candidates:
            try:
                return cast(ImageFont.ImageFont, ImageFont.truetype(path, font_size))
            except OSError:
                continue
        return cast(ImageFont.ImageFont, ImageFont.load_default())


def _fixed_digit_text(value: int, digits: int) -> str:
    """Return a right-aligned number constrained to a fixed digit field."""

    safe_value = max(0, value)
    text = str(safe_value)
    if len(text) > digits:
        return ">" + ("9" * max(1, digits - 1))
    return text.rjust(digits)
