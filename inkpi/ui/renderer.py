"""Main dashboard renderer composing all panels."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from typing import TYPE_CHECKING
from typing import cast

from PIL import Image
from PIL import ImageDraw, ImageFont

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
from inkpi.ui.drawing import draw_line, draw_rect, draw_text, truncate_text
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

        self._separator_width = 2
        self._status_height = 48
        self._github_height = 164
        self._codex_height = 116
        self._bottom_height = (
            self._content_height
            - self._status_height
            - self._github_height
            - self._codex_height
            - 3 * self._separator_width
        )

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
        y = CANVAS_PADDING

        self._render_status_bar(
            canvas,
            x=content_x,
            y=y,
            width=self._content_width,
            date_time=snapshot.date_time,
            weather=snapshot.weather,
        )
        y += self._status_height
        draw_line(
            canvas,
            (content_x, y, content_x + self._content_width, y),
            fill=GRAY_MID,
            width=self._separator_width,
        )
        y += self._separator_width

        github_img = self._github.render(github=snapshot.github)
        canvas.paste(github_img, (content_x, y))
        y += self._github_height
        draw_line(
            canvas,
            (content_x, y, content_x + self._content_width, y),
            fill=GRAY_MID,
            width=self._separator_width,
        )
        y += self._separator_width

        codex_img = self._codex.render(codex=snapshot.codex)
        canvas.paste(codex_img, (content_x, y))
        y += self._codex_height
        draw_line(
            canvas,
            (content_x, y, content_x + self._content_width, y),
            fill=GRAY_MID,
            width=self._separator_width,
        )
        y += self._separator_width

        self._render_bottom_status(
            canvas,
            x=content_x,
            y=y,
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
        draw = ImageDraw.Draw(image)
        small_font = self._load_font(FONT_SIZE_SMALL)

        date_text = date_time.now.strftime("%a %b %d %Y").upper()
        time_text = date_time.now.strftime("%H:%M")
        draw_text(image, (x + MARGIN, y + 9), date_text, fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL, font_weight="semibold")
        time_x = x + 215
        draw_text(image, (time_x, y + 9), time_text, fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL)

        weather_x = x + 310
        weather_text = self._format_weather(weather)
        draw_text(image, (weather_x, y + 9), weather_text, fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL)

        version_text = f"InkPi v{_inkpi_version()}"
        version_width = draw.textbbox((0, 0), version_text, font=small_font)[2]
        draw_text(
            image,
            (x + width - MARGIN - version_width, y + 12),
            version_text,
            fill=GRAY_LIGHT,
            font_size=FONT_SIZE_SMALL,
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
        column_gap = 20
        column_width = (width - column_gap) // 2
        system_x = x + MARGIN
        network_x = x + column_width + column_gap + MARGIN
        content_y = y + 8

        draw_text(image, (system_x, content_y), "SYSTEM PRESSURE", fill=GRAY_BLACK, font_size=FONT_SIZE_LARGE, font_weight="bold")
        metric_y = content_y + 32
        self._draw_fixed_percent(image, system_x, metric_y, "CPU", system.cpu_average_percent)
        self._draw_fixed_percent(image, system_x + 128, metric_y, "RAM", system.memory_percent)
        self._draw_fixed_percent(image, system_x + 256, metric_y, "LOAD", system.global_load_percent)

        bar_y = metric_y + 30
        bar_width = column_width - 2 * MARGIN
        load = max(0, min(100, system.global_load_percent))
        draw_rect(image, (system_x, bar_y, system_x + bar_width, bar_y + 12), fill=None, outline=GRAY_MID, width=1)
        fill_width = int(bar_width * load / 100)
        if fill_width > 0:
            draw_rect(image, (system_x, bar_y, system_x + fill_width, bar_y + 12), fill=GRAY_BLACK)

        sep_x = x + column_width + column_gap // 2
        draw_line(image, (sep_x, y + 8, sep_x, y + height - 8), fill=GRAY_LIGHT, width=1)

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
        value_font = self._load_font(FONT_SIZE_NORMAL)
        value_width = draw.textbbox((0, 0), value_text, font=value_font)[2]
        draw_text(image, (x, y + 2), label, fill=GRAY_MID, font_size=FONT_SIZE_SMALL)
        draw_text(image, (x + 92 - value_width, y), value_text, fill=GRAY_BLACK, font_size=FONT_SIZE_NORMAL, font_weight="semibold")

    @staticmethod
    def _format_weather(weather: WeatherInfo) -> str:
        if weather.temperature_celsius is not None:
            return f"{weather.temperature_celsius:>5.1f}C"
        return truncate_text(weather.summary, 18).ljust(18)

    @staticmethod
    def _network_label(network: NetworkInfo) -> str:
        if network.connection_type == "wifi":
            return f"WiFi {network.ssid}" if network.ssid else "WiFi"
        if network.connection_type == "ethernet":
            return "Ethernet"
        return "Offline" if not network.online else "Unknown"

    @staticmethod
    def _load_font(font_size: int) -> ImageFont.ImageFont:
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
