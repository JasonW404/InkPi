"""Left sidebar panel for datetime, weather, and system status."""

from __future__ import annotations

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
from src.ui.drawing import draw_rect, draw_text, truncate_text

if TYPE_CHECKING:
    from src.domain.models import DateTimeInfo, SystemStatus, WeatherInfo


class SidebarPanel:
    """Render datetime, weather, and system status in vertical layout."""

    def __init__(self, width: int, height: int) -> None:
        """Initialize panel dimensions.

        Args:
            width: Panel width in pixels.
            height: Panel height in pixels.
        """
        self._width = width
        self._height = height

    def render(
        self,
        date_time: DateTimeInfo,
        weather: WeatherInfo,
        system: SystemStatus,
    ) -> Image.Image:
        """Render sidebar panel content.

        Args:
            date_time: Current datetime information.
            weather: Current weather information.
            system: System load status.

        Returns:
            PIL image with rendered content.
        """
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        y = MARGIN

        # Artistic date layout with different emphasis for year/month/day.
        year_str = date_time.now.strftime("%Y")
        month_str = date_time.now.strftime("%m")
        day_str = date_time.now.strftime("%d")
        
        # Year in small gray.
        draw_text(image, (MARGIN, y), year_str, fill=GRAY_MID, font_size=FONT_SIZE_NORMAL)
        y += TEXT_LINE_HEIGHT
        
        # Month and day as large prominent display.
        month_day_str = f"{month_str} / {day_str}"
        draw_text(image, (MARGIN, y), month_day_str, fill=GRAY_BLACK, font_size=FONT_SIZE_TITLE)
        y += TITLE_LINE_HEIGHT + 15

        # Weather section.
        draw_text(image, (MARGIN, y), "Weather", fill=GRAY_MID, font_size=FONT_SIZE_NORMAL)
        y += TEXT_LINE_HEIGHT
        if weather.temperature_celsius is not None:
            temp_str = f"{weather.temperature_celsius:.1f}°C"
            draw_text(image, (MARGIN, y), temp_str, fill=GRAY_BLACK, font_size=FONT_SIZE_LARGE)
        else:
            draw_text(
                image,
                (MARGIN, y),
                truncate_text(weather.summary, 18),
                fill=GRAY_BLACK,
                font_size=FONT_SIZE_SMALL,
            )
        y += TITLE_LINE_HEIGHT + 15

        # System load section with icon representation.
        draw_text(image, (MARGIN, y), "System Load", fill=GRAY_MID, font_size=FONT_SIZE_NORMAL)
        y += TEXT_LINE_HEIGHT
        
        # Draw load level as filled squares (icon-style).
        square_size = 18
        square_spacing = 5
        icon_x = MARGIN
        icon_y = y
        
        for i in range(5):
            fill_color = GRAY_BLACK if i < system.load_level else GRAY_LIGHT
            square_x = icon_x + i * (square_size + square_spacing)
            draw_rect(
                image,
                (square_x, icon_y, square_x + square_size, icon_y + square_size),
                fill=fill_color,
                outline=GRAY_MID,
                width=1,
            )
        
        y += square_size + TEXT_LINE_HEIGHT
        load_pct_str = f"{system.load_percent:.1f}%"
        draw_text(image, (MARGIN, y), load_pct_str, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)

        return image
