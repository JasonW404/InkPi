"""Main dashboard renderer composing all panels."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from src.ui.constants import CANVAS_PADDING, GRAY_LIGHT, GRAY_WHITE, PANEL_SPACING, SCREEN_HEIGHT, SCREEN_WIDTH
from src.ui.drawing import draw_line
from src.ui.github_panel import GitHubPanel
from src.ui.knowledge_card_panel import KnowledgeCardPanel
from src.ui.sidebar_panel import SidebarPanel

if TYPE_CHECKING:
    from src.domain.models import DashboardSnapshot


class DashboardRenderer:
    """Compose full dashboard layout from individual panels."""

    def __init__(self, github_username: str = "", github_organization: str = "") -> None:
        """Initialize renderer with fixed layout dimensions.

        Args:
            github_username: GitHub username for display.
            github_organization: GitHub organization for display.
        """
        # Layout dimensions with canvas padding.
        self._canvas_padding = CANVAS_PADDING
        self._content_width = SCREEN_WIDTH - 2 * CANVAS_PADDING
        self._content_height = SCREEN_HEIGHT - 2 * CANVAS_PADDING
        
        self._sidebar_width = 220
        self._sidebar_height = self._content_height

        self._main_area_x = self._sidebar_width + PANEL_SPACING
        self._main_area_width = self._content_width - self._main_area_x

        self._card_height = 270
        self._github_height = self._content_height - self._card_height - PANEL_SPACING

        # Panel renderers.
        self._sidebar = SidebarPanel(self._sidebar_width, self._sidebar_height)
        self._card = KnowledgeCardPanel(self._main_area_width, self._card_height)
        self._github = GitHubPanel(
            self._main_area_width,
            self._github_height,
            github_username,
            github_organization,
        )

    def render(self, snapshot: DashboardSnapshot) -> Image.Image:
        """Render full dashboard from snapshot data.

        Args:
            snapshot: Complete dashboard data snapshot.

        Returns:
            PIL image at 800x480 resolution with 4-level grayscale.
        """
        # Create base canvas with padding.
        canvas = Image.new("L", (SCREEN_WIDTH, SCREEN_HEIGHT), GRAY_WHITE)

        # Render sidebar panel.
        sidebar_img = self._sidebar.render(
            date_time=snapshot.date_time,
            weather=snapshot.weather,
            system=snapshot.system,
        )
        canvas.paste(sidebar_img, (CANVAS_PADDING, CANVAS_PADDING))

        # Draw vertical separator after sidebar.
        sep_x = CANVAS_PADDING + self._sidebar_width
        draw_line(
            canvas,
            (sep_x, CANVAS_PADDING, sep_x, SCREEN_HEIGHT - CANVAS_PADDING),
            fill=GRAY_LIGHT,
            width=2,
        )

        # Render knowledge card panel (top-right).
        card_img = self._card.render(card=snapshot.card)
        card_x = CANVAS_PADDING + self._main_area_x
        canvas.paste(card_img, (card_x, CANVAS_PADDING))

        # Draw horizontal separator between card and GitHub panels.
        separator_y = CANVAS_PADDING + self._card_height
        draw_line(
            canvas,
            (card_x, separator_y, SCREEN_WIDTH - CANVAS_PADDING, separator_y),
            fill=GRAY_LIGHT,
            width=2,
        )

        # Render GitHub panel (bottom-right).
        github_img = self._github.render(github=snapshot.github)
        github_y = CANVAS_PADDING + self._card_height + PANEL_SPACING
        canvas.paste(github_img, (card_x, github_y))

        return canvas
