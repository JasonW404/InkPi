"""Compatibility wrapper for preview mode.

Preview functionality now lives in `main.py` as `preview()`.
"""

from __future__ import annotations

from main import preview


def main() -> None:
    """Render preview image using merged entrypoint logic."""

    preview()


if __name__ == "__main__":
    main()
