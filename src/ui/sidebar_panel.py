"""Left sidebar panel for datetime, weather, and system status."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from PIL import Image, ImageDraw, ImageFont

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
        self._width = width
        self._height = height

    def render(
        self,
        date_time: DateTimeInfo,
        weather: WeatherInfo,
        system: SystemStatus,
    ) -> Image.Image:
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        left_small = FONT_SIZE_NORMAL
        left_normal = FONT_SIZE_LARGE
        left_large = FONT_SIZE_TITLE
        left_title = 32
        date_year_size = left_normal
        date_main_size = left_title + 4
        temp_size = left_title

        y = MARGIN

        self._draw_bold_text(
            image,
            (MARGIN, y),
            "Weather",
            fill=GRAY_MID,
            font_size=left_normal,
        )
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

        self._draw_bold_text(
            image,
            (MARGIN, y),
            "System",
            fill=GRAY_MID,
            font_size=left_normal,
        )
        y += TEXT_LINE_HEIGHT + 6

        detail_size = FONT_SIZE_SMALL
        value_size = FONT_SIZE_NORMAL
        metrics_draw = ImageDraw.Draw(image)
        detail_font = self._load_font(detail_size)
        value_font = self._load_font(value_size)

        self._draw_bold_text(image, (MARGIN, y), "CPU", fill=GRAY_MID, font_size=left_small)
        y += TEXT_LINE_HEIGHT - 2

        cpu_x = MARGIN
        peak_label = "Peak"
        peak_value = f"{system.cpu_peak_percent:.0f}%"
        avg_label = "Avg"
        avg_value = f"{system.cpu_average_percent:.0f}%"

        draw_text(image, (cpu_x, y), peak_label, fill=GRAY_BLACK, font_size=detail_size)
        peak_label_w = metrics_draw.textbbox((0, 0), peak_label, font=detail_font)[2]

        peak_value_x = cpu_x + peak_label_w + 6
        peak_detail_bottom = metrics_draw.textbbox((0, 0), peak_label, font=detail_font)[3]
        peak_value_bottom = metrics_draw.textbbox((0, 0), peak_value, font=value_font)[3]
        peak_value_y = y + peak_detail_bottom - peak_value_bottom
        draw_text(
            image,
            (int(peak_value_x), int(peak_value_y)),
            peak_value,
            fill=GRAY_BLACK,
            font_size=value_size,
            font_weight="semibold",
        )
        peak_value_w = metrics_draw.textbbox((0, 0), peak_value, font=value_font)[2]

        avg_label_x = int(peak_value_x + peak_value_w + 18)
        draw_text(image, (avg_label_x, y), avg_label, fill=GRAY_BLACK, font_size=detail_size)
        avg_label_w = metrics_draw.textbbox((0, 0), avg_label, font=detail_font)[2]
        avg_value_x = avg_label_x + avg_label_w + 6
        avg_detail_bottom = metrics_draw.textbbox((0, 0), avg_label, font=detail_font)[3]
        avg_value_bottom = metrics_draw.textbbox((0, 0), avg_value, font=value_font)[3]
        avg_value_y = peak_value_y
        draw_text(
            image,
            (int(avg_value_x), int(avg_value_y)),
            avg_value,
            fill=GRAY_BLACK,
            font_size=value_size,
            font_weight="semibold",
        )

        y += TEXT_LINE_HEIGHT + 4

        self._draw_bold_text(image, (MARGIN, y), "RAM", fill=GRAY_MID, font_size=left_small)
        y += TEXT_LINE_HEIGHT - 2

        mem_used_value_text = f"{system.memory_used_gb:.1f}"
        mem_total_text = f"/{system.memory_total_gb:.1f}G"
        mem_percent_text = f"{system.memory_percent:.0f}%"

        mem_used_bbox = metrics_draw.textbbox((0, 0), mem_used_value_text, font=value_font)
        mem_total_bbox = metrics_draw.textbbox((0, 0), mem_total_text, font=detail_font)
        mem_percent_bbox = metrics_draw.textbbox((0, 0), mem_percent_text, font=value_font)

        mem_used_w = mem_used_bbox[2] - mem_used_bbox[0]
        mem_total_w = mem_total_bbox[2] - mem_total_bbox[0]
        mem_used_bottom = mem_used_bbox[3]
        mem_total_bottom = mem_total_bbox[3]
        mem_percent_bottom = mem_percent_bbox[3]

        shared_bottom_y = y + max(mem_used_bottom, mem_total_bottom, mem_percent_bottom)
        mem_used_y = shared_bottom_y - mem_used_bottom
        mem_total_y = shared_bottom_y - mem_total_bottom + 1
        mem_percent_y = shared_bottom_y - mem_percent_bottom

        draw_text(
            image,
            (MARGIN, int(mem_used_y)),
            mem_used_value_text,
            fill=GRAY_BLACK,
            font_size=value_size,
            font_weight="semibold",
        )
        mem_total_x = MARGIN + mem_used_w
        draw_text(
            image,
            (int(mem_total_x), int(mem_total_y)),
            mem_total_text,
            fill=GRAY_BLACK,
            font_size=detail_size,
        )

        mem_percent_x = mem_total_x + mem_total_w + 16
        draw_text(
            image,
            (int(mem_percent_x), int(mem_percent_y)),
            mem_percent_text,
            fill=GRAY_BLACK,
            font_size=value_size,
            font_weight="semibold",
        )

        y += TEXT_LINE_HEIGHT + 4

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

        month_str = date_time.now.strftime("%m")
        day_str = date_time.now.strftime("%d")
        year_str = date_time.now.strftime("%Y")

        draw = ImageDraw.Draw(image)
        date_font = self._load_font(date_main_size)
        year_font = self._load_font(date_year_size)
        month_bbox = draw.textbbox((0, 0), month_str, font=date_font)
        day_bbox = draw.textbbox((0, 0), day_str, font=date_font)
        year_bbox = draw.textbbox((0, 0), year_str, font=year_font)

        month_width = month_bbox[2] - month_bbox[0]
        month_height = month_bbox[3] - month_bbox[1]
        day_width = day_bbox[2] - day_bbox[0]
        day_height = day_bbox[3] - day_bbox[1]
        day_bottom = day_bbox[3]
        year_bottom = year_bbox[3]

        stack_gap = 6
        bottom_lift = 8
        day_y = int(self._height - MARGIN - day_height - bottom_lift)
        month_y = int(day_y - stack_gap - month_height)

        draw_text(image, (MARGIN, month_y), month_str, fill=GRAY_BLACK, font_size=date_main_size)
        draw_text(image, (MARGIN, day_y), day_str, fill=GRAY_BLACK, font_size=date_main_size)

        year_gap = 12
        stack_width = max(month_width, day_width)
        year_x = int(MARGIN + stack_width + year_gap)
        year_y = int(day_y + day_bottom - year_bottom)
        draw_text(image, (year_x, year_y), year_str, fill=GRAY_MID, font_size=date_year_size)

        return image

    @staticmethod
    def _draw_bold_text(
        image: Image.Image,
        xy: tuple[int, int],
        text: str,
        fill: int,
        font_size: int,
    ) -> None:
        """Render text with crisp edges."""

        draw_text(image, xy, text, fill=fill, font_size=font_size, font_weight="semibold")

    @staticmethod
    def _load_font(font_size: int) -> ImageFont.ImageFont:
        """Load UI font for measurements with fallback."""

        candidates = [
            "assets/fonts/MapleMono-CN-Regular.ttf",
            "assets/fonts/MapleMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            try:
                return cast(ImageFont.ImageFont, ImageFont.truetype(path, font_size))
            except OSError:
                continue
        return cast(ImageFont.ImageFont, ImageFont.load_default())
