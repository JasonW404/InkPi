"""Main dashboard renderer composing all panels."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from src.ui.codex_panel import CodexPanel
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
        self._canvas_padding = CANVAS_PADDING
        self._content_width = SCREEN_WIDTH - 2 * CANVAS_PADDING
        self._content_height = SCREEN_HEIGHT - 2 * CANVAS_PADDING

        self._codex_height = 110
        self._sidebar_height = self._content_height - self._codex_height

        self._sidebar_width = 200

        self._main_area_x = self._sidebar_width + PANEL_SPACING
        self._main_area_width = self._content_width - self._main_area_x

        self._card_height = 120
        self._github_height = self._sidebar_height - self._card_height - PANEL_SPACING

        self._sidebar = SidebarPanel(self._sidebar_width, self._sidebar_height)
        self._card = KnowledgeCardPanel(self._main_area_width, self._card_height)
        self._github = GitHubPanel(
            self._main_area_width,
            self._github_height,
            github_username,
            github_organization,
        )
        self._codex = CodexPanel(self._content_width, self._codex_height)

    def render(self, snapshot: DashboardSnapshot) -> Image.Image:
        """Render full dashboard from snapshot data.

        Args:
            snapshot: Complete dashboard data snapshot.

        Returns:
            PIL image at 800x480 resolution with 4-level grayscale.
        """
        canvas = Image.new("L", (SCREEN_WIDTH, SCREEN_HEIGHT), GRAY_WHITE)

        sidebar_img = self._sidebar.render(
            date_time=snapshot.date_time,
            weather=snapshot.weather,
            system=snapshot.system,
            network=snapshot.network,
        )
        canvas.paste(sidebar_img, (CANVAS_PADDING, CANVAS_PADDING))

        sep_x = CANVAS_PADDING + self._sidebar_width
        draw_line(
            canvas,
            (sep_x, CANVAS_PADDING, sep_x, CANVAS_PADDING + self._sidebar_height),
            fill=GRAY_LIGHT,
            width=2,
        )

        right_x = CANVAS_PADDING + self._main_area_x

        card_img = self._card.render(card=snapshot.card)
        canvas.paste(card_img, (right_x, CANVAS_PADDING))

        sep_y1 = CANVAS_PADDING + self._card_height
        draw_line(
            canvas,
            (right_x, sep_y1, SCREEN_WIDTH - CANVAS_PADDING, sep_y1),
            fill=GRAY_LIGHT,
            width=2,
        )

        github_y = CANVAS_PADDING + self._card_height + PANEL_SPACING
        github_img = self._github.render(github=snapshot.github)
        canvas.paste(github_img, (right_x, github_y))

        codex_band_y = CANVAS_PADDING + self._sidebar_height
        draw_line(
            canvas,
            (CANVAS_PADDING, codex_band_y, SCREEN_WIDTH - CANVAS_PADDING, codex_band_y),
            fill=GRAY_LIGHT,
            width=2,
        )

        codex_img = self._codex.render(codex=snapshot.codex)
        canvas.paste(codex_img, (CANVAS_PADDING, codex_band_y))

        return canvas
