"""GitHub statistics panel renderer."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from PIL import Image

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
from src.ui.drawing import draw_line, draw_rect, draw_text, truncate_text

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

        # Calculate column widths for 3-column layout.
        # Each column has internal padding for better spacing.
        col_spacing = MARGIN
        col_padding = 6  # Internal padding within each column.
        col_width = (self._width - 2 * MARGIN - 2 * col_spacing) // 3
        
        # Base positions for each column.
        col1_x_base = MARGIN
        col2_x_base = MARGIN + col_width + col_spacing
        col3_x_base = MARGIN + (col_width + col_spacing) * 2
        
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
            font_size=FONT_SIZE_TITLE,
        )
        y += TITLE_LINE_HEIGHT + 5

        # Column 1: User statistics (left).
        self._render_user_stats(image, col1_x, y, col_width, github)

        # Column 2: 5-week contribution calendar (center).
        self._render_contribution_calendar(image, col2_x, y, col_width, github)

        # Column 3: Organization statistics (right).
        self._render_org_stats(image, col3_x, y, col_width, github)

        # Draw vertical separators between columns.
        separator_x1 = col1_x_base + col_width + col_spacing // 2
        separator_x2 = col2_x_base + col_width + col_spacing // 2
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
    ) -> None:
        """Render user statistics in left column."""
        # User label with underline.
        user_label = truncate_text(self._username, 18)
        draw_text(image, (x, y), user_label, fill=GRAY_BLACK, font_size=FONT_SIZE_LARGE)
        y += 26
        
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
                font_size=FONT_SIZE_NORMAL,
            )
            y += TEXT_LINE_HEIGHT
            draw_text(
                image,
                (x, y),
                f"Days: {len(github.contributions)}",
                fill=GRAY_MID,
                font_size=FONT_SIZE_SMALL,
            )
        else:
            draw_text(
                image,
                (x, y),
                "No data",
                fill=GRAY_MID,
                font_size=FONT_SIZE_SMALL,
            )

    def _render_org_stats(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        github: GitHubMonthlyStats,
    ) -> None:
        """Render organization statistics in right column."""
        # Org label with underline.
        org_label = truncate_text(self._organization, 18)
        draw_text(image, (x, y), org_label, fill=GRAY_BLACK, font_size=FONT_SIZE_LARGE)
        y += 26
        
        # Draw underline beneath organization name.
        draw_line(image, (x, y, x + width - 20, y), fill=GRAY_MID, width=1)
        y += 10

        # Organization stats.
        draw_text(
            image,
            (x, y),
            f"Repos: {github.organization_repo_count}",
            fill=GRAY_BLACK,
            font_size=FONT_SIZE_NORMAL,
        )
        y += TEXT_LINE_HEIGHT
        draw_text(
            image,
            (x, y),
            f"Commits: {github.organization_monthly_commit_count}",
            fill=GRAY_BLACK,
            font_size=FONT_SIZE_NORMAL,
        )
        y += TEXT_LINE_HEIGHT
        draw_text(
            image,
            (x, y),
            f"+{github.organization_additions}",
            fill=GRAY_BLACK,
            font_size=FONT_SIZE_SMALL,
        )
        y += TEXT_LINE_HEIGHT
        draw_text(
            image,
            (x, y),
            f"-{github.organization_deletions}",
            fill=GRAY_MID,
            font_size=FONT_SIZE_SMALL,
        )

    def _render_contribution_calendar(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        github: GitHubMonthlyStats,
    ) -> None:
        """Render 5-week contribution calendar in center column."""
        # Center the calendar grid within the column.
        calendar_x = x + 5
        draw_text(image, (calendar_x, y), "Last 5 Weeks", fill=GRAY_MID, font_size=FONT_SIZE_SMALL)
        y += TEXT_LINE_HEIGHT + 2

        if not github.contributions:
            draw_text(
                image,
                (calendar_x, y),
                "No activity",
                fill=GRAY_LIGHT,
                font_size=FONT_SIZE_SMALL,
            )
            return

        # Build a 5-week grid (7 days × 5 weeks = 35 days).
        # Each week is a row, each day is a column.
        today = date.today()
        start_date = today - timedelta(days=34)  # Go back 4 weeks + current week.

        # Create contribution map for quick lookup.
        contrib_map = {day.day: day.commit_count for day in github.contributions}

        # Calendar grid parameters (larger cells for better visibility).
        cell_size = min(12, (width - MARGIN) // 7)
        cell_spacing = 3

        for week in range(5):
            week_y = y + week * (cell_size + cell_spacing)
            for day in range(7):
                current_date = start_date + timedelta(days=week * 7 + day)
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

                cell_x = calendar_x + day * (cell_size + cell_spacing)
                draw_rect(
                    image,
                    (cell_x, week_y, cell_x + cell_size, week_y + cell_size),
                    fill=fill,
                    outline=GRAY_MID,
                    width=1,
                )
