"""Main dashboard renderer composing all panels."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from math import cos, pi, sin
from typing import TYPE_CHECKING

from PIL import Image
from PIL import ImageDraw

from inkpi.ui.codex_panel import CodexPanel
from inkpi.ui.constants import (
    CANVAS_PADDING,
    FONT_SIZE_LARGE,
    FONT_SIZE_NORMAL,
    FONT_SIZE_SMALL,
    GRAY_BLACK,
    GRAY_LIGHT,
    GRAY_MID,
    GRAY_WHITE,
    MARGIN,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from inkpi.ui.drawing import _load_font, draw_line, draw_rect, draw_text, truncate_text
from inkpi.ui.github_panel import GitHubPanel

if TYPE_CHECKING:
    from inkpi.domain.models import DashboardSnapshot, NetworkInfo, SystemStatus, WeatherInfo


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

        self._separator_width = 1
        self._status_x_offset = MARGIN
        self._status_y = 8
        self._status_height = 41
        self._status_github_separator_y = 52
        self._github_y = 59
        self._github_height = 176
        self._github_codex_separator_y = 241
        self._codex_y = 248
        self._codex_height = 118
        self._codex_bottom_separator_y = 372
        self._bottom_y = 379
        self._bottom_height = 96

        self._github = GitHubPanel(
            self._content_width,
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

        content_x = CANVAS_PADDING
        status_x = content_x + self._status_x_offset
        status_width = self._content_width - self._status_x_offset

        self._render_status_bar(
            canvas,
            x=status_x,
            y=self._status_y,
            width=status_width,
            date_time=snapshot.date_time,
            weather=snapshot.weather,
        )
        draw_line(
            canvas,
            (
                content_x,
                self._status_github_separator_y,
                content_x + self._content_width,
                self._status_github_separator_y,
            ),
            fill=GRAY_MID,
            width=self._separator_width,
        )

        github_img = self._github.render(github=snapshot.github)
        canvas.paste(github_img, (content_x, self._github_y))
        draw_line(
            canvas,
            (
                content_x,
                self._github_codex_separator_y,
                content_x + self._content_width,
                self._github_codex_separator_y,
            ),
            fill=GRAY_MID,
            width=self._separator_width,
        )

        codex_img = self._codex.render(codex=snapshot.codex)
        canvas.paste(codex_img, (content_x, self._codex_y))
        draw_line(
            canvas,
            (
                content_x,
                self._codex_bottom_separator_y,
                content_x + self._content_width,
                self._codex_bottom_separator_y,
            ),
            fill=GRAY_MID,
            width=self._separator_width,
        )

        self._render_bottom_status(
            canvas,
            x=content_x,
            y=self._bottom_y,
            width=self._content_width,
            height=self._bottom_height,
            system=snapshot.system,
            network=snapshot.network,
        )

        return canvas

    def _render_status_bar(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        date_time,
        weather: WeatherInfo,
    ) -> None:
        date_text = date_time.now.strftime("%a %b %d %Y").upper()
        draw_text(image, (x, y + 3), date_text, fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL, font_weight="semibold")

        self._render_weather_component(
            image,
            center_x=x + width // 2,
            y=y + 3,
            weather=weather,
        )

        version_text = f"InkPi v{_inkpi_version()}"
        draw_text(
            image,
            (x + 609, y + 3),
            version_text,
            fill=GRAY_LIGHT,
            font_size=FONT_SIZE_NORMAL,
        )

    def _render_bottom_status(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        system: SystemStatus,
        network: NetworkInfo,
    ) -> None:
        system_x = x + MARGIN
        network_x = x + 401
        content_y = y + 8

        draw_text(image, (system_x, content_y), "SYSTEM PRESSURE", fill=GRAY_BLACK, font_size=FONT_SIZE_LARGE, font_weight="bold")
        metric_y = content_y + 30
        self._draw_fixed_percent(image, system_x, metric_y, "CPU", system.cpu_average_percent)
        self._draw_fixed_percent(image, system_x + 125, metric_y, "RAM", system.memory_percent)
        self._draw_fixed_percent(image, system_x + 250, metric_y, "LOAD", system.global_load_percent)

        bar_y = content_y + 64
        bar_width = 360
        load = max(0, min(100, system.global_load_percent))
        draw_rect(image, (system_x, bar_y, system_x + bar_width, bar_y + 12), fill=None, outline=GRAY_MID, width=1)
        fill_width = int(bar_width * load / 100)
        if fill_width > 0:
            draw_rect(image, (system_x, bar_y, system_x + fill_width, bar_y + 12), fill=GRAY_BLACK)

        sep_x = x + 390
        draw_line(image, (sep_x, y + 8, sep_x, y + height - 12), fill=GRAY_LIGHT, width=1)

        draw_text(image, (network_x, content_y), "NETWORK", fill=GRAY_BLACK, font_size=FONT_SIZE_LARGE, font_weight="bold")
        network_label = self._network_label(network)
        draw_text(image, (network_x, metric_y), truncate_text(network_label, 24), fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL)
        draw_text(image, (network_x, metric_y + 28), _fixed_ip(network.ip_address), fill=GRAY_MID, font_size=FONT_SIZE_SMALL)

    def _draw_fixed_percent(
        self,
        image: Image.Image,
        x: int,
        y: int,
        label: str,
        value: float,
    ) -> None:
        draw = ImageDraw.Draw(image)
        value_text = f"{max(0, min(999, round(value))):>3}%"
        value_font = _load_font(FONT_SIZE_NORMAL)
        value_width = draw.textbbox((0, 0), value_text, font=value_font)[2]
        label_width = draw.textbbox((0, 0), label, font=_load_font(FONT_SIZE_SMALL))[2]
        draw_text(image, (x, y + 2), label, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)
        draw_text(image, (x + label_width + 10, y), value_text, fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL, font_weight="semibold")

    @staticmethod
    def _format_weather(weather: WeatherInfo) -> str:
        if weather.temperature_celsius is not None:
            return f"{weather.temperature_celsius:>5.1f}C"
        return truncate_text(weather.summary, 18).ljust(18)

    def _render_weather_component(
        self,
        image: Image.Image,
        center_x: int,
        y: int,
        weather: WeatherInfo,
    ) -> None:
        """Render centered temperature text with a compact weather icon."""

        draw = ImageDraw.Draw(image)
        weather_text = self._format_weather(weather)
        font = _load_font(FONT_SIZE_NORMAL)
        text_width = draw.textbbox((0, 0), weather_text, font=font)[2]
        icon_size = 28 if weather.temperature_celsius is not None else 0
        gap = 8 if icon_size else 0
        total_width = text_width + gap + icon_size
        text_x = int(center_x - total_width / 2)
        draw_text(image, (text_x, y), weather_text, fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL)
        if icon_size:
            self._draw_weather_icon(
                image,
                icon_name=weather.icon,
                x=text_x + text_width + gap,
                y=y,
                size=icon_size,
            )

    def _draw_weather_icon(
        self,
        image: Image.Image,
        icon_name: str,
        x: int,
        y: int,
        size: int,
    ) -> None:
        draw = ImageDraw.Draw(image)
        if icon_name == "clear":
            center = (x + size // 2, y + size // 2)
            radius = max(4, size // 4)
            draw.ellipse(
                (
                    center[0] - radius,
                    center[1] - radius,
                    center[0] + radius,
                    center[1] + radius,
                ),
                fill=GRAY_BLACK,
                outline=GRAY_BLACK,
            )
            inner_ray = radius + 2
            outer_ray = size // 2 - 1
            for index in range(8):
                angle = index * pi / 4
                draw.line(
                    (
                        center[0] + int(cos(angle) * inner_ray),
                        center[1] + int(sin(angle) * inner_ray),
                        center[0] + int(cos(angle) * outer_ray),
                        center[1] + int(sin(angle) * outer_ray),
                    ),
                    fill=GRAY_BLACK,
                    width=2,
                )
            return

        if icon_name in {"partly_cloudy", "fog"}:
            cloud_y = y + size // 2
            draw.ellipse((x + 2, cloud_y - 4, x + 10, cloud_y + 4), outline=GRAY_BLACK, width=2)
            draw.ellipse((x + 8, cloud_y - 7, x + 17, cloud_y + 4), outline=GRAY_BLACK, width=2)
            draw.line((x + 3, cloud_y + 4, x + 18, cloud_y + 4), fill=GRAY_BLACK, width=2)
            return

        if icon_name in {"rain", "rain_showers", "drizzle", "thunderstorm", "thunderstorm_hail"}:
            self._draw_weather_icon(image, "partly_cloudy", x, y - 2, size)
            for offset in (5, 10, 15):
                draw.line((x + offset, y + 15, x + offset - 2, y + 19), fill=GRAY_BLACK, width=1)
            return

        if icon_name in {"snow", "snow_showers"}:
            for offset in (5, 10, 15):
                cx = x + offset
                cy = y + 15
                draw.line((cx - 3, cy, cx + 3, cy), fill=GRAY_BLACK, width=1)
                draw.line((cx, cy - 3, cx, cy + 3), fill=GRAY_BLACK, width=1)
            return

        draw.rectangle((x + 3, y + 3, x + size - 3, y + size - 3), outline=GRAY_BLACK, width=2)

    @staticmethod
    def _network_label(network: NetworkInfo) -> str:
        if network.connection_type == "wifi":
            return f"WiFi {network.ssid}" if network.ssid else "WiFi"
        if network.connection_type == "ethernet":
            return "Ethernet"
        return "Offline" if not network.online else "Unknown"

def _fixed_ip(value: str) -> str:
    if not value:
        return "---.---.---.---"
    parts = value.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        return ".".join(parts)
    return truncate_text(value, 15).ljust(15)


def _inkpi_version() -> str:
    try:
        return pkg_version("inkpi")
    except Exception:  # noqa: BLE001
        return "dev"
