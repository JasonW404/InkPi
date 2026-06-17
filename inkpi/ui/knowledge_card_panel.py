"""Knowledge card panel renderer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from inkpi.ui.constants import (
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
from inkpi.ui.drawing import draw_rect, draw_text, truncate_text

if TYPE_CHECKING:
    from inkpi.domain.models import KnowledgeCard


class KnowledgeCardPanel:
    """Render knowledge card with title and body text."""

    def __init__(self, width: int, height: int) -> None:
        """Initialize panel dimensions.

        Args:
            width: Panel width in pixels.
            height: Panel height in pixels.
        """
        self._width = width
        self._height = height

    def render(self, card: KnowledgeCard) -> Image.Image:
        """Render knowledge card content.

        Args:
            card: Knowledge card data.

        Returns:
            PIL image with rendered content.
        """
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        title_size = FONT_SIZE_TITLE
        body_size = FONT_SIZE_NORMAL
        meta_size = FONT_SIZE_NORMAL

        y = MARGIN

        # Card title.
        title_lines = self._wrap_text(card.title, max_chars=31)
        for line in title_lines[:2]:  # Max 2 title lines.
            draw_text(image, (MARGIN, y), line, fill=GRAY_BLACK, font_size=title_size)
            y += TITLE_LINE_HEIGHT

        y += 8

        # Card body with wrapping.
        body_lines = self._wrap_text(card.body, max_chars=44)
        max_body_lines = (self._height - y - MARGIN) // TEXT_LINE_HEIGHT
        for line in body_lines[:max_body_lines]:
            draw_text(image, (MARGIN, y), line, fill=GRAY_BLACK, font_size=body_size)
            y += TEXT_LINE_HEIGHT

        # Source label at bottom.
        source_y = self._height - MARGIN - TEXT_LINE_HEIGHT
        source_text = truncate_text(f"Source: {card.source}", 40)
        draw_text(image, (MARGIN, source_y), source_text, fill=GRAY_BLACK, font_size=meta_size)

        return image

    @staticmethod
    def _wrap_text(text: str, max_chars: int) -> list[str]:
        """Simple word-wrap text to max characters per line.

        Args:
            text: Input text.
            max_chars: Maximum characters per line.

        Returns:
            List of wrapped lines.
        """
        words = text.split()
        lines: list[str] = []
        current_line: list[str] = []
        current_length = 0

        for word in words:
            word_length = len(word) + (1 if current_line else 0)
            if current_length + word_length > max_chars and current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += word_length

        if current_line:
            lines.append(" ".join(current_line))

        return lines
