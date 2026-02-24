"""UI rendering constants for 4-level grayscale eInk display."""

from __future__ import annotations

# Screen dimensions (landscape orientation).
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

# 4-level grayscale palette (0=white, 255=black).
GRAY_WHITE = 255
GRAY_LIGHT = 140
GRAY_MID = 60
GRAY_BLACK = 0

# Layout margins and spacing.
CANVAS_PADDING = 15
MARGIN = 15
PANEL_SPACING = 8
TEXT_LINE_HEIGHT = 24
TITLE_LINE_HEIGHT = 30

# Font sizes (logical sizes, actual loading may vary).
# Increased for 4.26" e-ink display readability.
FONT_SIZE_SMALL = 16
FONT_SIZE_NORMAL = 19
FONT_SIZE_LARGE = 23
FONT_SIZE_TITLE = 27
