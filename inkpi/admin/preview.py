"""Dashboard preview rendering for the admin portal."""

from __future__ import annotations

from io import BytesIO

from inkpi.dashboard.pages.overview import OverviewPage
from inkpi.dashboard.preview_data import make_mock_overview_snapshot

SUPPORTED_PREVIEW_PAGES = {"overview"}


def render_mock_page_png(page_id: str) -> bytes:
    """Render a deterministic dashboard page preview as PNG bytes."""

    if page_id != "overview":
        raise ValueError(f"unsupported preview page: {page_id}")

    page = OverviewPage()
    image = page.render(make_mock_overview_snapshot())
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
