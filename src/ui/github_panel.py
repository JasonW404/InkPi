"""GitHub statistics panel renderer."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

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
        """Initialize panel dimensions and identity labels.

        Args:
            width: Panel width in pixels.
            height: Panel height in pixels.
            username: GitHub username for display.
            organization: GitHub organization for display.
        """
        self._width = width
        self._height = height
        self._username = username or "User"
        self._organization = organization or "Org"

    def render(self, github: GitHubMonthlyStats) -> Image.Image:
        """Render GitHub panel in 3-column layout.

        Args:
            github: Monthly GitHub statistics.

        Returns:
            PIL image with rendered content.
        """
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        # Right-bottom GitHub text: +1 size for readability.
        title_size = FONT_SIZE_TITLE + 1
        label_size = FONT_SIZE_LARGE + 1
        body_size = FONT_SIZE_NORMAL + 1
        meta_size = FONT_SIZE_SMALL + 1

        # Calculate asymmetric 3-column widths:
        # left/right columns stay equal width, center calendar keeps minimum width.
        col_spacing = MARGIN
        col_padding = 6
        content_width = self._width - 2 * MARGIN - 2 * col_spacing
        min_calendar_width = 94
        preferred_calendar_width = 102
        max_calendar_width = 118
        col2_width = min(
            max_calendar_width,
            max(min_calendar_width, int(content_width * 0.24), preferred_calendar_width),
        )
        remaining = max(0, content_width - col2_width)
        col1_width = remaining // 2
        col3_width = remaining - col1_width

        # Base positions for each column.
        col1_x_base = MARGIN
        col2_x_base = col1_x_base + col1_width + col_spacing
        col3_x_base = col2_x_base + col2_width + col_spacing
        
        # Content positions with internal padding.
        col1_x = col1_x_base + col_padding
        col2_x = col2_x_base + col_padding
        col3_x = col3_x_base + col_padding

        y = MARGIN

        # Title spanning full width (no month needed since sidebar shows date).
        draw_text(
            image,
            (MARGIN, y),
            "GitHub",
            fill=GRAY_BLACK,
            font_size=title_size,
        )
        y += TITLE_LINE_HEIGHT + 5

        # Column 1: User statistics (left).
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

        # Column 2: 5-week contribution calendar (center).
        self._render_contribution_calendar(image, col2_x, y, col2_width, github, meta_size)

        # Column 3: Organization statistics (right).
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

        # Draw vertical separators between columns.
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
        """Render user statistics in left column."""
        # User label with dynamic font fitting.
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
        
        # Draw underline beneath username.
        draw_line(image, (x, y, x + width - 20, y), fill=GRAY_MID, width=1)
        y += 10

        # Contribution count.
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
        """Render organization statistics in right column."""
        # Org label with dynamic font fitting.
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
        
        # Draw underline beneath organization name.
        draw_line(image, (x, y, x + width - 20, y), fill=GRAY_MID, width=1)
        y += 10

        # Organization stats.
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
        """Render 5-week contribution calendar in center column."""
        # Header for calendar with short text to preserve space.
        draw_text(image, (x + 2, y), "5 Weeks", fill=GRAY_MID, font_size=meta_size)
        y += TEXT_LINE_HEIGHT + 2

        # Compute compact grid geometry to fit a 7×5 calendar
        # (7 weekdays × 5 weeks). Weeks are rendered as columns,
        # weekdays as rows to match common contribution calendars.
        grid_padding = 6
        cell_spacing = 3
        weeks = 5
        days = 7
        available_width = max(1, width - grid_padding * 2)
        # Determine a slightly larger cell_size while ensuring it fits.
        cell_size = max(9, min(14, (available_width - (weeks - 1) * cell_spacing) // weeks))
        grid_width = weeks * cell_size + (weeks - 1) * cell_spacing
        calendar_x = x + max(0, (width - grid_width) // 2)

        if not github.contributions:
            draw_text(
                image,
                (calendar_x, y),
                "No activity",
                fill=GRAY_LIGHT,
                font_size=meta_size,
            )
            return
        # Build a 5-week grid (7 days × 5 weeks = 35 days).
        # Weeks are columns and weekdays are rows.
        today = date.today()
        start_date = today - timedelta(days=34)  # Go back 4 weeks + current week.

        # Create contribution map for quick lookup (date -> commit_count).
        contrib_map = {d.day: d.commit_count for d in github.contributions}

        for week in range(weeks):
            for day_idx in range(days):
                current_date = start_date + timedelta(days=week * 7 + day_idx)
                if current_date > today:
                    continue

                # Get commit count for this day.
                commit_count = contrib_map.get(current_date, 0)

                # Map to grayscale intensity.
                if commit_count == 0:
                    fill = GRAY_WHITE
                elif commit_count <= 2:
                    fill = GRAY_LIGHT
                elif commit_count <= 5:
                    fill = GRAY_MID
                else:
                    fill = GRAY_BLACK

                cell_x = calendar_x + week * (cell_size + cell_spacing)
                cell_y = y + day_idx * (cell_size + cell_spacing)
                draw_rect(
                    image,
                    (cell_x, cell_y, cell_x + cell_size, cell_y + cell_size),
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
        """Fit label text into given width by reducing font size then truncating.

        Args:
            image: Target image for measuring text.
            text: Original text.
            max_width: Maximum render width in pixels.
            preferred_size: Initial font size.
            min_size: Lower bound of font size.

        Returns:
            Tuple of (fitted text, fitted font size).
        """

        draw = ImageDraw.Draw(image)
        text_value = text.strip() or "-"

        for size in range(preferred_size, min_size - 1, -1):
            font = self._load_font(size)
            text_width = draw.textbbox((0, 0), text_value, font=font)[2]
            if text_width <= max_width:
                return text_value, size

        # If still too long at min size, apply hard truncation.
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
            return ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                font_size,
            )
        except OSError:
            return ImageFont.load_default()
