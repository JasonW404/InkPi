# AI Coding Guidelines for eInk Dashboard

## Project Overview
E-ink dashboard for Raspberry Pi 4B + Waveshare 4.26inch (800x480) display. Renders weather, GitHub stats, system load, and knowledge cards with intelligent refresh strategies (partial 60s / full 3600s).

## Architecture Layers (understand before contributing)
1. **Config** [src/config.py](../src/config.py): Environment-driven configuration with frozen dataclasses (ScreenConfig, RefreshConfig, GitHubConfig, WeatherConfig)
2. **Domain** [src/domain/models.py](../src/domain/models.py): Immutable frozen dataclasses for data contracts (DashboardSnapshot, GitHubMonthlyStats, WeatherInfo, etc.)
3. **Services** [src/services/](../src/services/): Protocol-based providers implementing contracts from [contracts.py](../src/services/contracts.py); each returns dropdown-safe frozen domain objects
4. **Rendering** [src/ui/](../src/ui/): Layout panels (SidebarPanel, GitHubPanel, KnowledgeCardPanel) -> DashboardRenderer -> grayscale PIL Image
5. **Display** [src/display/](../src/display/): EPDAdapter wraps waveshare_epd hardware; DirtyRegionTracker optimizes partial refreshes
6. **App Runtime** [src/app.py](../src/app.py), [main.py](../main.py): RefreshPolicy orchestrates cycles using monotonic time; DashboardApplication manages signal handlers and graceful shutdown

## Critical Patterns
- **Service Contracts**: Pass Protocol-typed deps (DateTimeProvider, WeatherProvider, etc.), NOT concrete classes. Use dependency injection in constructors.
- **Domain-Driven**: All services return frozen dataclasses from `src.domain.models`—never raw API responses. Providers fail gracefully, returning fallback data.
- **Configuration**: All dynamic values via AppConfig with environment variable overrides; no hardcoded defaults except in @dataclass defaults.
- **Refresh Strategy**: Full refresh when `elapsed_since_full >= full_refresh_interval_seconds` OR `partial_streak_limit` exceeded. Check hours, not raw seconds [Full rules](../docs/ai/instructions/refresh-policy-rules.md).

## Naming & Code Organization
- **Naming**: *Config (config classes), *Service/*Provider (data providers), *Panel/*Renderer (UI components), *Adapter (hardware abstraction)
- **Docstrings**: Google style with module description, Args/Returns for complex functions. Skip trivial comments.
- **Type Hints**: Always annotate; use type imports with `from __future__ import annotations`
- **Errors**: Catch external API failures; log with context (provider name, operation, params); return fallback data to prevent main loop crash

## Development Environment
- **Python**: 3.12 only; managed via `uv`
- **Commands**: `uv sync` (install deps), `uv run` (execute), avoid `python -m venv` or `pip`
- **Preview**: `uv run python preview.py` generates `preview.png` for layout validation
- **Service Mode**: `sudo systemctl [start|stop|status] eink-dashboard.service` (runs [eink-dashboard.service](../scripts/systemd/eink-dashboard.service))
- **Logging**: Check [docs/ai/instructions/](../docs/ai/instructions/) for quality gates, architectural rules, and refresh policy specifics

## Integration Points
- **GitHub**: Requires API key for private repos; uses GitHub v3 REST; monthly contribution calendar + org stats [GitHubService](../src/services/github.py)
- **Weather**: Open-Meteo (no key needed by default); supports location names or lat,long coords [WeatherService](../src/services/weather.py)
- **System**: psutil for CPU/memory; load_level computed as 0-5 buckets [SystemService](../src/services/system.py)
- **Knowledge Cards**: Local JSON + optional remote source; see [data/cards.json](../data/cards.json) [KnowledgeCardService](../src/services/posts.py)

## Testing & Validation
- Static type checking via Pylance
- Run preview frequently during UI changes to validate grayscale/layout before hardware test
- Coordinate with existing systemd service when debugging hardware display

---
See [docs/architecture-overview.md](../docs/architecture-overview.md) and instruction subdirectory for deeper context.
