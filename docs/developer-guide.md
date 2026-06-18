# InkPi Developer Guide

## Purpose

This guide explains how to develop, test, extend, and deploy InkPi without
breaking its module ownership boundaries. Read
[inkpi-architecture.md](inkpi-architecture.md) first for the runtime design and
[../AGENTS.md](../AGENTS.md) for the current codebase status.

## Repository Layout

- `inkpi/core.py`: main orchestration service and control request routing.
- `inkpi/display/`: independent display service, refresh policy, and hardware
  ownership.
- `inkpi/dashboard/`: page contract, registry, rotation, and built-in pages.
- `inkpi/management/`: system/network facts and future management foundations.
- `inkpi/contracts.py`: versioned DTOs and cross-module protocols.
- `inkpi/ipc.py`: JSON-over-Unix-socket transport.
- `src/`: legacy overview providers, renderer, and Waveshare adapter retained
  during migration.
- `config/inkpi.example.json`: non-secret runtime configuration example.
- `scripts/systemd/`: service templates and deployment installer.
- `tests/`: legacy and InkPi architecture/runtime tests.

## Ownership Rules

- Only `inkpi-display` may access SPI/GPIO or choose full, partial, or skipped
  refresh behavior.
- Dashboard pages return complete `800x480` grayscale PIL images. They do not
  request refresh modes or import display implementations.
- `inkpi-core` owns configuration persistence, scheduling, and service
  orchestration.
- Management owns system and network facts. Dashboard pages consume those facts
  through contracts.
- Cross-process and cross-module public behavior uses typed contracts from
  `inkpi/contracts.py`.
- Secrets remain in `.env` or service environment configuration, never in
  `config.json`.

## Local Setup

InkPi requires Python 3.12 and uses `uv` exclusively.

```bash
uv sync --extra dev
uv run pytest -q
uv run python -m compileall -q inkpi src tests
```

Do not install the `rpi` dependency group on non-Linux development machines.
On the Raspberry Pi:

```bash
uv sync --extra rpi
```

## Preview Pages

Render pages without display hardware:

```bash
uv run inkpi-preview overview --mock-data --output tmp/overview.png
uv run inkpi-preview overview --output tmp/overview-live.png
```

Every page must render an exact `800x480` grayscale image. Preview both changed
and failure states when modifying a page. Use `--mock-data` for fast UI layout
iteration without network or Codex subprocess collection.

## Run Services Locally

Use temporary sockets so local processes do not require the systemd-managed
`/run/inkpi-display` and `/run/inkpi-core` directories:

```bash
uv run inkpi-display --socket /tmp/inkpi-display.sock
```

In a second terminal:

```bash
INKPI_REFRESH_SECONDS=10 uv run inkpi-core \
  --socket /tmp/inkpi-core.sock \
  --display-socket /tmp/inkpi-display.sock \
  --config /tmp/inkpi-config.json
```

Query and control the running core:

```bash
uv run inkpi-ctl --socket /tmp/inkpi-core.sock status
uv run inkpi-ctl --socket /tmp/inkpi-core.sock pages
uv run inkpi-ctl --socket /tmp/inkpi-core.sock page codex_usage disable
```

On machines without Waveshare hardware, the display adapter runs in simulation
mode while preserving refresh-policy behavior.

## Add A Dashboard Page

1. Implement the `DashboardPage` contract under `inkpi/dashboard/pages/`.
2. Give the page a stable `page_id` and human-readable `name`.
3. Keep collection and rendering logic independent from display hardware.
4. Inject management facts or other data providers through contracts.
5. Register the page explicitly in the core composition root.
6. Add the page to the example configuration.
7. Add render-size, failure, configuration, and rotation tests.
8. Generate and inspect a preview.

Pages must degrade into a renderable failure state where practical. Unhandled
page failures are isolated by core, recorded in status, and skipped until the
next scheduled attempt.

## Change Display Behavior

Display-policy changes belong only in `inkpi/display/`.

Required invariants:

- complete frame input;
- serialized hardware access;
- obsolete normal pending frames may be replaced by the newest frame;
- immediate frames cannot be displaced by normal frames;
- page changes and recovery use full refresh;
- failed refreshes invalidate frame history;
- the default longevity policy forces full refresh after five partials;
- service shutdown puts the panel to sleep.

Add focused engine tests using a fake backend before hardware validation.

## Configuration And Contracts

`inkpi-core` loads and atomically writes versioned JSON configuration. Any new
editable field must have:

- a typed configuration field;
- validation and a safe default;
- backward-compatible parsing for the current schema version, or a deliberate
  schema-version migration;
- tests for valid and invalid values;
- documentation in `config/inkpi.example.json`.

Contract changes must preserve the `CONTRACT_VERSION` protocol or deliberately
increment it with matching server/client changes.

## Quality Gates

Before deployment:

```bash
uv sync --extra dev
uv run pytest -q
uv run python -m compileall -q inkpi src tests
git diff --check
uv build
```

For display or orchestration changes, also run the local two-service smoke test
and inspect both page previews.

## Raspberry Pi Deployment

The deployment target is available through `ssh meta_pi`. The intended checkout
path is `/home/meta/Documents/InkPi`.

After synchronizing the repository:

```bash
cd ~/Documents/InkPi
uv sync --extra rpi
sudo bash scripts/systemd/install_inkpi_services.sh
systemctl status inkpi-display.service inkpi-core.service
uv run inkpi-ctl pages
```

The installer disables the legacy `eink-dashboard.service`. Never run the
legacy monolithic service concurrently with `inkpi-display`.

When using `rsync`, exclude `.venv`, generated build/cache files, logs, and the
live `.lgd-*` GPIO runtime FIFO.

Validate deployment with:

```bash
journalctl -u inkpi-display.service -u inkpi-core.service --since "10 minutes ago"
uv run inkpi-ctl status
uv run inkpi-ctl pages
```

Confirm the physical display shows both pages over a rotation cycle. The Codex
page requires an installed, logged-in Codex CLI; without it, the page should
show its unavailable state without harming the service.

## Future Management Work

The future portal should run independently from display refresh work. It will
consume the typed core client and delegate privileged NetworkManager changes to
a narrow helper. Do not place arbitrary shell execution or privileged network
operations in dashboard pages, core request handlers, or the portal process.
