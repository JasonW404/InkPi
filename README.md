# InkPi

InkPi is a modular Raspberry Pi appliance for an 800x480 Waveshare 4.26-inch
e-ink display. It preserves the original overview dashboard and adds a native
Codex usage page, page rotation, local controls, and contracts for a future Pi
management portal.

## Runtime Services

- `inkpi-core`: orchestrates page collection, rendering, rotation, configuration,
  management facts, and dashboard controls.
- `inkpi-display`: exclusively owns SPI/GPIO, panel lifecycle, frame history,
  and every full/partial/skip refresh decision.
- `inkpi-ctl`: queries and controls a running core service.
- `inkpi-preview`: renders either built-in page without display hardware.

Dashboard pages submit complete grayscale frames. They cannot select a refresh
mode or access the Waveshare driver.

## Development

InkPi uses Python 3.12 and `uv`.

```bash
uv sync --extra dev
uv run pytest -q
uv run inkpi-preview overview
uv run inkpi-preview codex_usage
```

Pi-only GPIO/SPI dependencies are isolated from local development:

```bash
uv sync --extra dev --extra rpi
```

The overview page continues to use `.env` for secrets and source-specific
settings. InkPi's non-secret runtime configuration is stored at
`~/.config/inkpi/config.json`; see
[`config/inkpi.example.json`](config/inkpi.example.json).

## Run Locally

Use temporary sockets when running outside systemd:

```bash
INKPI_DISPLAY_SOCKET=/tmp/inkpi-display.sock uv run inkpi-display
INKPI_DISPLAY_SOCKET=/tmp/inkpi-display.sock \
INKPI_CORE_SOCKET=/tmp/inkpi-core.sock \
uv run inkpi-core
uv run inkpi-ctl --socket /tmp/inkpi-core.sock pages
```

## Raspberry Pi Deployment

Install both system services from the repository:

```bash
uv sync --extra rpi
sudo bash scripts/systemd/install_inkpi_services.sh
systemctl status inkpi-display.service inkpi-core.service
```

The installer disables the legacy `eink-dashboard.service` so only
`inkpi-display` can own the physical panel.

## Built-In Pages

- `overview`: weather, system load, knowledge card, and GitHub statistics.
- `codex_usage`: native PIL rendering of Codex subscription usage. Live data
  requires an installed and logged-in Codex CLI on the Pi.

Enable or disable pages through the local core contract:

```bash
uv run inkpi-ctl pages
uv run inkpi-ctl page codex_usage disable
uv run inkpi-ctl page codex_usage enable
```

At least one page must remain enabled.

## Architecture

See [docs/inkpi-architecture.md](docs/inkpi-architecture.md) for module
ownership, contracts, refresh strategy, and future management integration.

Development workflow and extension guidance live in
[docs/developer-guide.md](docs/developer-guide.md). Contributors and agents
must follow [AGENTS.md](AGENTS.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
