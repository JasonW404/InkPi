# InkPi Agent And Codebase Declaration

All contributors and coding agents working in this repository must follow
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Current Status

- Project name: **InkPi**
- Version: `0.2.0`
- Target: Raspberry Pi 4B with Waveshare 4.26-inch `800x480` e-ink HAT
- Architecture: hybrid multi-process runtime
- Main services: `inkpi-core` and `inkpi-display`
- Built-in pages: `overview` and `codex_usage`
- Configuration: versioned JSON owned by core, secrets supplied through `.env`
- Management state: read-only system/network facts and dashboard controls exist;
  web portal and NetworkManager write controls are future work
- Migration state: the legacy `src/` package remains for overview data/rendering
  and the Waveshare adapter; new ownership and orchestration belong in `inkpi/`
- Deployment target: `meta_pi:/home/meta/Documents/InkPi`

## Non-Negotiable Boundaries

1. `inkpi-display` is the sole SPI/GPIO and physical-panel owner.
2. Full, partial, skipped, and recovery refresh decisions happen only inside
   `inkpi/display/`.
3. Dashboard pages submit complete logical frames and cannot request refresh
   modes or import display implementations.
4. `inkpi-core` owns scheduling, service orchestration, and atomic configuration
   persistence.
5. Management owns system/network facts. Dashboard and management share data or
   controls only through typed contracts.
6. Cross-process APIs use versioned contracts over local Unix sockets.
7. Slow collection, rendering, or display refresh must not block control/status
   requests.
8. At least one dashboard page must remain enabled.
9. Secrets must not enter editable JSON configuration, logs, tests, or docs.

## Engineering Rules

- Use Python 3.12 and `uv`; never use `pip`, `python -m venv`, or `virtualenv`.
- Keep Pi-only dependencies in the `rpi` optional dependency group.
- Preserve existing user changes and staged work.
- Extend current contracts and modules before inventing parallel abstractions.
- Keep new display-driver dependencies and policy out of dashboard/management.
- Keep privileged network operations out of core and the future portal; use a
  narrowly scoped helper.
- Update architecture and developer documentation when boundaries or operations
  change.

## Required Verification

For normal changes:

```bash
uv sync --extra dev
uv run pytest -q
uv run python -m compileall -q inkpi src tests
git diff --check
```

For packaging or entrypoint changes, also run `uv build`.

For page changes, render and inspect the relevant `inkpi-preview` output.

For display, service, or deployment changes, run a local two-service smoke test
and then validate on `meta_pi`. Clearly report whether verification was
simulation-only or used the physical panel.

## Deployment and Real-World Testing

- Use `ssh meta_pi` to access the target device.
- Deploy with local `.env` file.

## Key References

- [Developer Guide](docs/developer-guide.md)
- [Architecture](docs/inkpi-architecture.md)
- [Example Configuration](config/inkpi.example.json)
- [Engineering Guidelines](.github/copilot-instructions.md)
