"""Drawing utilities for grayscale rendering."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal

from PIL import ImageDraw, ImageFont

from src.ui.constants import FONT_SIZE_NORMAL, GRAY_BLACK

if TYPE_CHECKING:
    from PIL import Image


FontWeight = Literal["regular", "medium", "semibold", "bold"]


@lru_cache(maxsize=64)
def _load_font(font_size: int, font_weight: FontWeight) -> ImageFont.ImageFont:
    weight_candidates: dict[FontWeight, list[str]] = {
        "regular": [
            "MapleMono-CN-Regular.ttf",
            "MapleMono.ttf",
        ],
        "medium": [
            "MapleMono-CN-Medium.ttf",
            "MapleMono-CN-Regular.ttf",
            "MapleMono.ttf",
        ],
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

    font_dir = Path("assets/fonts")
    for filename in weight_candidates.get(font_weight, weight_candidates["regular"]):
        font_path = font_dir / filename
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), font_size)
            except OSError:
                continue

    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except OSError:
        return ImageFont.load_default()


def draw_text(
    image: Image.Image,
    xy: tuple[int, int],
    text: str,
    fill: int = GRAY_BLACK,
    font_size: int = FONT_SIZE_NORMAL,
    font_weight: FontWeight = "regular",
) -> None:
    """Draw text at specified position.

    Args:
        image: Target PIL image.
        xy: Top-left coordinate.
        text: Text content to draw.
        fill: Grayscale fill color (0-255).
        font_size: Logical font size.
        font_weight: Font weight for MapleMono selection.
    """
    draw = ImageDraw.Draw(image)
    font = _load_font(font_size, font_weight)
    draw.text(xy, text, fill=fill, font=font)


def draw_rect(
    image: Image.Image,
    box: tuple[int, int, int, int],
    fill: int | None = None,
    outline: int | None = None,
    width: int = 1,
) -> None:
    """Draw rectangle with optional fill and outline.

    Args:
        image: Target PIL image.
        box: Bounding box as (x0, y0, x1, y1).
        fill: Fill color (0-255) or None.
        outline: Outline color (0-255) or None.
        width: Outline width in pixels.
    """
    draw = ImageDraw.Draw(image)
    draw.rectangle(box, fill=fill, outline=outline, width=width)


def draw_line(
    image: Image.Image,
    xy: tuple[int, int, int, int],
    fill: int,
    width: int = 1,
) -> None:
    """Draw a line between two points.

    Args:
        image: Target PIL image.
        xy: Line coordinates as (x0, y0, x1, y1).
        fill: Line color (0-255).
        width: Line width in pixels.
    """
    draw = ImageDraw.Draw(image)
    draw.line(xy, fill=fill, width=width)


def truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to max length with ellipsis.

    Args:
        text: Input text.
        max_chars: Maximum character count.

    Returns:
        Truncated text with '...' suffix if needed.
    """
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."
