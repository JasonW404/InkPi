# InkPi Architecture

## Ownership Model

InkPi uses strict module ownership with a hybrid process model:

- `inkpi-core` is the main orchestrator and configuration authority.
- `inkpi-display` is a separate process and the sole physical display owner.
- `dashboard` is an independently testable module loaded by core.
- `management` owns system and network facts and will later back `inkpi-admin`.
- `contracts` contains versioned immutable DTOs shared across boundaries.

Unix sockets carry versioned JSON requests between services. Complete frames
are transported as PNG payloads. Refresh modes are intentionally absent from
the public display contract.

## Data Flow

1. Core asks the dashboard controller to render the active page.
2. The page collects data through service or management contracts and returns
   an 800x480 grayscale image.
3. Core submits the complete frame and page metadata to `inkpi-display`.
4. Display serializes requests, replaces obsolete pending normal frames, selects
   a refresh action, drives the panel, and returns structured telemetry.
5. Core exposes page controls and status for the future admin portal.

## Display Strategy

The Waveshare 4.26-inch driver sends a complete buffer even for its partial
refresh waveform. Dirty-region analysis is therefore a decision input, not a
rectangular transfer mechanism.

The longevity policy:

- skips frames without meaningful visual changes;
- uses partial refresh only for small monochrome-compatible same-page changes;
- uses full four-gray refresh for page changes, grayscale-only changes, large
  changes, startup/recovery, and uncertain controller state;
- forces full refresh after five successful partial refreshes by default;
- relies on the hardware adapter to reinitialize when transitioning from
  partial to full;
- reinitializes after repeated display failures;
- exposes counts, last action/reason, failures, and queue depth.

Automatic deep sleep between refreshes is intentionally deferred until it is
validated on the physical HAT. The service sleeps the panel during shutdown.

## Configuration And Controls

Core owns versioned JSON configuration and writes it atomically. Page controls
are validated and idempotent; disabling the final enabled page is rejected.
Secrets remain in environment variables rather than portal-editable JSON.

Current local controls:

- `get_pages`
- `set_page_enabled`
- `get_dashboard_status`
- `get_display_status`
- `get_system_status`
- `get_network_status`

## Future Management

The future `inkpi-admin` process will consume core contracts while serving the
LAN/hotspot portal. Privileged NetworkManager changes will be delegated to a
narrow helper rather than executed by dashboard or admin code. This keeps
portal requests responsive and prevents display refreshes from blocking system
configuration.
