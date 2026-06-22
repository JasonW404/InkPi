"""Left sidebar panel for weather, date, system status, and network."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

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
from inkpi.ui.drawing import _load_font, _load_icon_font, draw_rect, draw_text, truncate_text

if TYPE_CHECKING:
    from inkpi.domain.models import DateTimeInfo, NetworkInfo, SystemStatus, WeatherInfo


class SidebarPanel:
    """Render weather, date, system metrics, and network in vertical layout."""

    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    def render(
        self,
        date_time: DateTimeInfo,
        weather: WeatherInfo,
        system: SystemStatus,
        network: NetworkInfo,
    ) -> Image.Image:
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)

        y = MARGIN

        temp_size = FONT_SIZE_TITLE
        if weather.temperature_celsius is not None:
            temp_str = f"{weather.temperature_celsius:.1f}°C"
            icon_str = self._weather_icon(weather.icon)
            icon_font = _load_icon_font(temp_size)
            draw = ImageDraw.Draw(image)
            draw.text((MARGIN, y), icon_str, fill=GRAY_BLACK, font=icon_font)
            icon_width = draw.textbbox((0, 0), icon_str, font=icon_font)[2]
            
            draw_text(image, (MARGIN + icon_width + 8, y), temp_str, fill=GRAY_BLACK, font_size=temp_size)
        else:
            draw_text(
                image,
                (MARGIN, y),
                truncate_text(weather.summary, 18),
                fill=GRAY_BLACK,
                font_size=FONT_SIZE_NORMAL,
            )
        y += TITLE_LINE_HEIGHT + 4

        date_line = date_time.now.strftime("%a %b %d").upper()
        draw_text(image, (MARGIN, y), date_line, fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL, font_weight="semibold")
        y += TEXT_LINE_HEIGHT

        year_str = date_time.now.strftime("%Y")
        draw_text(image, (MARGIN, y), year_str, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)
        y += TEXT_LINE_HEIGHT + 20

        detail_size = FONT_SIZE_SMALL
        value_size = FONT_SIZE_NORMAL
        metrics_draw = ImageDraw.Draw(image)
        detail_font = _load_font(detail_size)
        value_font = _load_font(value_size)

        self._draw_bold_text(image, (MARGIN, y), "CPU", fill=GRAY_MID, font_size=FONT_SIZE_SMALL)
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

        self._draw_bold_text(image, (MARGIN, y), "RAM", fill=GRAY_MID, font_size=FONT_SIZE_SMALL)
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

        bar_height = 16
        bar_width = self._width - 2 * MARGIN
        load = max(0, min(100, system.global_load_percent))

        draw_rect(
            image,
            (MARGIN, y, MARGIN + bar_width, y + bar_height),
            fill=None,
            outline=GRAY_MID,
            width=1,
        )
        fill_width = int(bar_width * load / 100)
        if fill_width > 0:
            draw_rect(
                image,
                (MARGIN, y, MARGIN + fill_width, y + bar_height),
                fill=GRAY_BLACK,
            )

        y += bar_height + 6
        global_text = f"Global {system.global_load_percent:.0f}%"
        draw_text(image, (MARGIN, y), global_text, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)

        y += TEXT_LINE_HEIGHT + 8

        if network.connection_type == "wifi":
            ssid = network.ssid or ""
            network_label = f"WiFi {ssid}" if ssid else "WiFi"
            network_label = truncate_text(network_label, 18)
        elif network.connection_type == "ethernet":
            network_label = "Ethernet"
        else:
            network_label = "Offline" if not network.online else "Unknown"

        draw_text(image, (MARGIN, y), network_label, fill=GRAY_BLACK, font_size=FONT_SIZE_SMALL)
        y += TEXT_LINE_HEIGHT

        ip_text = network.ip_address if network.ip_address else "No IP"
        draw_text(image, (MARGIN, y), ip_text, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)

        version_text = f"InkPi v{_inkpi_version()}"
        version_font = _load_font(FONT_SIZE_SMALL)
        draw = ImageDraw.Draw(image)
        version_w = draw.textbbox((0, 0), version_text, font=version_font)[2]
        draw_text(
            image,
            (self._width - MARGIN - version_w, self._height - MARGIN - FONT_SIZE_SMALL),
            version_text,
            fill=GRAY_LIGHT,
            font_size=FONT_SIZE_SMALL,
        )

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
    def _weather_icon(icon_name: str) -> str:
        icon_map = {
            "clear": "☀",
            "partly_cloudy": "⛅",
            "fog": "☁",
            "drizzle": "☂",
            "rain": "☔",
            "snow": "❄",
            "rain_showers": "☔",
            "snow_showers": "❅",
            "thunderstorm": "⛈",
            "thunderstorm_hail": "⚡",
        }
        return icon_map.get(icon_name, "?")

def _inkpi_version() -> str:
    """Return installed InkPi package version, or 'dev' if unavailable."""

    try:
        return pkg_version("inkpi")
    except Exception:  # noqa: BLE001
        return "dev"
