"""Native Codex subscription usage page."""

from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from PIL import Image, ImageDraw

from src.ui.drawing import _load_font


class CodexCollectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class UsageWindow:
    label: str
    remaining_percent: float
    resets_at: str | None


@dataclass(frozen=True)
class CodexUsageSnapshot:
    ok: bool
    plan: str
    updated_at: str
    windows: list[UsageWindow]
    error: str | None = None


class CodexUsagePage:
    page_id = "codex_usage"
    name = "Codex Usage"

    def collect(self) -> CodexUsageSnapshot:
        try:
            return self._collect_live()
        except Exception as error:
            return CodexUsageSnapshot(
                ok=False,
                plan="UNAVAILABLE",
                updated_at=_now(),
                windows=[],
                error=str(error),
            )

    def render(self, snapshot: CodexUsageSnapshot) -> Image.Image:
        image = Image.new("L", (800, 480), 255)
        draw = ImageDraw.Draw(image)
        title = _load_font(42, "bold")
        normal = _load_font(18, "regular")
        small = _load_font(14, "regular")
        percent_font = _load_font(66, "bold")
        draw.text((28, 18), "CODEX", fill=0, font=title)
        draw.text((174, 18), "USAGE", fill=80, font=title)
        draw.text((535, 26), snapshot.plan.upper(), fill=0, font=normal)
        draw.text((690, 29), "LIVE" if snapshot.ok else "STALE", fill=0, font=small)
        draw.line((28, 78, 772, 78), fill=0, width=2)

        if not snapshot.windows:
            draw.text((28, 130), "USAGE UNAVAILABLE", fill=0, font=title)
            draw.multiline_text((30, 205), snapshot.error or "No quota windows returned.", fill=60, font=normal, spacing=8)
            return image

        for index, window in enumerate(snapshot.windows[:2]):
            top = 100 + index * 178
            remaining = max(0, min(100, window.remaining_percent))
            draw.text((30, top), f"{window.label} REMAINING", fill=0, font=small)
            draw.rectangle((30, top + 38, 520, top + 82), outline=0, width=2)
            draw.rectangle((30, top + 38, 30 + int(490 * remaining / 100), top + 82), fill=0)
            draw.text((555, top + 24), f"{remaining:.0f}%", fill=0, font=percent_font)
            draw.text((30, top + 100), f"RESET IN  {_countdown(window.resets_at)}", fill=50, font=normal)
            draw.line((28, top + 148, 772, top + 148), fill=0, width=2)
        return image

    def _collect_live(self) -> CodexUsageSnapshot:
        executable = shutil.which(os.getenv("CODEX_BINARY", "codex"))
        if not executable:
            raise CodexCollectorError("Codex CLI not found; install it and run `codex login`.")
        process = subprocess.Popen(
            [executable, "-s", "read-only", "-a", "untrusted", "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        try:
            self._request(process, 1, "initialize", {"clientInfo": {"name": "inkpi", "version": "0.2.0"}})
            self._send(process, {"method": "initialized", "params": {}})
            limits_result = self._request(process, 2, "account/rateLimits/read")
            account_result = self._request(process, 3, "account/read")
        finally:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()

        limits = limits_result.get("rateLimits", limits_result)
        account = account_result.get("account") or {}
        windows = [
            window
            for window in (
                _window(limits.get("primary"), "5-HOUR WINDOW"),
                _window(limits.get("secondary"), "WEEKLY WINDOW"),
            )
            if window
        ]
        if windows and windows[0].label == "5-HOUR WINDOW" and (limits.get("primary") or {}).get("windowDurationMins") == 10080:
            windows[0] = UsageWindow("WEEKLY WINDOW", windows[0].remaining_percent, windows[0].resets_at)
        return CodexUsageSnapshot(
            ok=True,
            plan=str(account.get("planType") or limits.get("planType") or "--"),
            updated_at=_now(),
            windows=windows,
        )

    @staticmethod
    def _send(process: subprocess.Popen[str], payload: dict[str, Any]) -> None:
        if not process.stdin:
            raise CodexCollectorError("Codex app-server stdin unavailable")
        process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        process.stdin.flush()

    def _request(
        self,
        process: subprocess.Popen[str],
        request_id: int,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._send(process, {"id": request_id, "method": method, "params": params or {}})
        deadline = time.monotonic() + float(os.getenv("CODEX_DASHBOARD_RPC_TIMEOUT", "20"))
        while time.monotonic() < deadline:
            if not process.stdout:
                break
            ready, _, _ = select.select([process.stdout], [], [], max(0, deadline - time.monotonic()))
            if not ready:
                break
            message = json.loads(process.stdout.readline())
            if message.get("id") == request_id:
                if message.get("error"):
                    raise CodexCollectorError(str(message["error"]))
                return message.get("result") or {}
        raise CodexCollectorError(f"Codex app-server timed out during `{method}`")


def _window(raw: dict[str, Any] | None, label: str) -> UsageWindow | None:
    if not raw:
        return None
    reset = raw.get("resetsAt", raw.get("reset_at"))
    if isinstance(reset, (int, float)):
        reset = datetime.fromtimestamp(reset, UTC).isoformat().replace("+00:00", "Z")
    used = float(raw.get("usedPercent", raw.get("used_percent", 0)))
    return UsageWindow(label, max(0, 100 - used), reset if isinstance(reset, str) else None)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _countdown(value: str | None) -> str:
    if not value:
        return "--"
    try:
        reset = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "--"
    seconds = max(0, int((reset - datetime.now(UTC)).total_seconds()))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    return f"{days}D {hours:02}:{minutes:02}" if days else f"{hours:02}:{minutes:02}"
