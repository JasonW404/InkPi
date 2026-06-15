from __future__ import annotations

from src.runtime.ghosting import GhostingGuard
from src.runtime.refresh_policy import RefreshMode, RefreshPolicy

from conftest import make_config


def test_refresh_policy_returns_partial_before_threshold(monkeypatch) -> None:
    ticks = iter([100.0, 101.0])
    monkeypatch.setattr("src.runtime.refresh_policy.time.monotonic", lambda: next(ticks))

    config = make_config(full_interval=999, max_partial_before_full=5)
    policy = RefreshPolicy(config)
    decision = policy.decide()

    assert decision.mode == RefreshMode.PARTIAL
    assert decision.reason == "regular_partial_refresh"


def test_refresh_policy_forces_full_on_partial_count(monkeypatch) -> None:
    ticks = iter([100.0, 101.0, 102.0])
    monkeypatch.setattr("src.runtime.refresh_policy.time.monotonic", lambda: next(ticks))

    config = make_config(full_interval=999, max_partial_before_full=1)
    policy = RefreshPolicy(config)

    first = policy.decide()
    second = policy.decide()

    assert first.mode == RefreshMode.PARTIAL
    assert second.mode == RefreshMode.FULL
    assert second.reason == "partial_refresh_threshold_reached"


def test_refresh_policy_forces_full_on_elapsed_time(monkeypatch) -> None:
    ticks = iter([10.0, 12.1])
    monkeypatch.setattr("src.runtime.refresh_policy.time.monotonic", lambda: next(ticks))

    config = make_config(full_interval=2, max_partial_before_full=99)
    policy = RefreshPolicy(config)
    decision = policy.decide()

    assert decision.mode == RefreshMode.FULL
    assert decision.reason == "full_refresh_interval_elapsed"


def test_ghosting_guard_large_change_upgrades() -> None:
    guard = GhostingGuard("balanced")
    assert guard.should_upgrade_for_large_change(0.41)
    assert not guard.should_upgrade_for_large_change(0.39)


def test_ghosting_guard_overlap_streak_forces_full() -> None:
    guard = GhostingGuard("balanced")
    bbox = (10, 10, 100, 100)

    for _ in range(3):
        guard.register_refresh(was_partial=True, has_changes=True, bbox=bbox)

    assert guard.should_force_full(bbox, dirty_ratio=0.07)
