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

        # Left sidebar fonts should be larger for readability.
        left_small = FONT_SIZE_SMALL + 2
        left_normal = FONT_SIZE_NORMAL + 2
        left_large = FONT_SIZE_LARGE + 2
        left_title = FONT_SIZE_TITLE + 2
        date_year_size = left_normal + 1
        date_main_size = left_title + 2
        temp_size = left_large + 2

        y = MARGIN

        # Artistic date layout with different emphasis for year/month/day.
        year_str = date_time.now.strftime("%Y")
        month_str = date_time.now.strftime("%m")
        day_str = date_time.now.strftime("%d")
        
        # Year in small gray.
        draw_text(image, (MARGIN, y), year_str, fill=GRAY_MID, font_size=date_year_size)
        y += TEXT_LINE_HEIGHT
        
        # Month and day as large prominent display.
        month_day_str = f"{month_str} / {day_str}"
        draw_text(image, (MARGIN, y), month_day_str, fill=GRAY_BLACK, font_size=date_main_size)
        y += TITLE_LINE_HEIGHT + 18

        # Weather section.
        draw_text(image, (MARGIN, y), "Weather", fill=GRAY_MID, font_size=left_normal)
        y += TEXT_LINE_HEIGHT
        if weather.temperature_celsius is not None:
            temp_str = f"{weather.temperature_celsius:.1f}°C"
            draw_text(image, (MARGIN, y), temp_str, fill=GRAY_BLACK, font_size=temp_size)
        else:
            draw_text(
                image,
                (MARGIN, y),
                truncate_text(weather.summary, 18),
                fill=GRAY_BLACK,
                font_size=left_small,
            )
        y += TITLE_LINE_HEIGHT + 18

        # System load section.
        draw_text(image, (MARGIN, y), "System", fill=GRAY_MID, font_size=left_normal)
        y += TEXT_LINE_HEIGHT

        cpu_summary = f"CPU P:{system.cpu_peak_percent:.0f}% A:{system.cpu_average_percent:.0f}%"
        draw_text(image, (MARGIN, y), cpu_summary, fill=GRAY_BLACK, font_size=left_small)
        y += TEXT_LINE_HEIGHT

        mem_summary = f"MEM {system.memory_used_gb:.1f}/{system.memory_total_gb:.1f}G"
        draw_text(image, (MARGIN, y), mem_summary, fill=GRAY_BLACK, font_size=left_small)
        y += TEXT_LINE_HEIGHT

        mem_percent_text = f"Mem {system.memory_percent:.0f}%"
        draw_text(image, (MARGIN, y), mem_percent_text, fill=GRAY_MID, font_size=left_small)
        y += TEXT_LINE_HEIGHT + 2

        # Draw global load as 8 bars.
        bar_count = 8
        bar_width = 18
        bar_spacing = 4
        bar_height = 14
        filled_bars = min(bar_count, max(0, round((system.global_load_percent / 100.0) * bar_count)))

        for index in range(bar_count):
            fill_color = GRAY_BLACK if index < filled_bars else GRAY_LIGHT
            bar_x = MARGIN + index * (bar_width + bar_spacing)
            draw_rect(
                image,
                (bar_x, y, bar_x + bar_width, y + bar_height),
                fill=fill_color,
                outline=GRAY_MID,
                width=1,
            )

        y += bar_height + 6
        global_text = f"Global {system.global_load_percent:.0f}%"
        draw_text(image, (MARGIN, y), global_text, fill=GRAY_MID, font_size=left_small)

        return image
