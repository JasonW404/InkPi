# AI Coding Guidelines for eInk Dashboard

## Project Snapshot
- Raspberry Pi 4B + Waveshare 4.26" (800x480) grayscale dashboard.

## Architecture You Must Preserve
1. **Config layer**: `src/config.py` builds frozen config dataclasses from `.env` + env vars (`AppConfig.from_env()`).
2. **Domain layer**: `src/domain/models.py` contains frozen data contracts shared across services and UI.
3. **Service layer**: `src/services/contracts.py` defines provider Protocols; implementations return domain objects (no raw API payloads).
4. **Aggregation**: `src/services/dashboard.py` uses `ThreadPoolExecutor` to fetch datetime/weather/github/card concurrently, then system metrics.
5. **Rendering**: `src/ui/renderer.py` composes `SidebarPanel` + `KnowledgeCardPanel` + `GitHubPanel` into fixed 800x480 grayscale output.
6. **Display/runtime**: `src/app.py` + `src/display/` run refresh policy, dirty-region detection, ghosting mitigation, and lifecycle screens.

## Runtime Data Flow (critical)
- `main.py` wires providers and starts preview (`preview()`) or hardware loop (`DashboardApplication.run()`).
- `DashboardApplication` behavior to keep:
	- startup screen -> initial snapshot -> forced full refresh baseline
	- refresh policy by monotonic time + partial counter (`RefreshPolicy`)
	- dirty check via `DirtyRegionTracker.compare()` before deciding display action
	- ghosting override can upgrade partial decision to full (`_should_force_full_for_ghosting`)
	- graceful SIGINT/SIGTERM shutdown screen then display sleep

## Service & Error Patterns (project-specific)
- Keep dependency injection Protocol-typed in constructors (see `DashboardDataService`).
- Provider failures should degrade, not crash loop:
	- `WeatherService`: returns `unavailable:<reason>` fallback
	- `KnowledgeCardService`: local-first, optional remote override, fallback card
- `GitHubService` uses token-aware private-data access and TTL cache.
- External HTTP calls use explicit timeouts (8-12s in current services).

## Developer Workflows
- Environment: Python 3.12 via `uv` only.
- Install/sync: `uv sync`
- Preview image: `uv run python main.py --preview` (or `uv run python preview.py` compatibility wrapper)
- Hardware run: `uv run python main.py`
- Long hardware soak: `scripts/hardware_24h_test.sh --hours 24`
- Systemd install/upgrade: `sudo bash scripts/systemd/install_service.sh`
- Service ops: `sudo systemctl status eink-dashboard.service`, logs via `journalctl -u eink-dashboard.service -f`

## Conventions in This Repo
- Naming: `*Config`, `*Service`/`*Provider`, `*Panel`/`*Renderer`, `*Adapter`.
- Module docstrings + typed signatures are standard; keep `from __future__ import annotations`.
- UI work should be validated with preview image before hardware testing.

## Integration Notes
- GitHub: REST v3 + pagination + commit-stat aggregation (`src/services/github.py`).
- Weather: Open-Meteo forecast + geocoding APIs (`src/services/weather.py`).
- System metrics: parsed from `/proc/stat` and `/proc/meminfo` (not psutil).
- Waveshare driver is optional at runtime; adapter supports simulation when hardware import fails.
