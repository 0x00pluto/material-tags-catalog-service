"""BuildLock 单测。"""

from __future__ import annotations

import threading

from src.catalog_service.build_lock import BuildLock
from src.catalog_service.models import BuildResult


def _fake_result(trigger: str, written: int = 1) -> BuildResult:
    return BuildResult(
        written=written,
        skipped=0,
        duration_ms=1,
        trigger=trigger,
        out_path="/tmp/x.jsonl",
    )


def test_request_runs_immediately() -> None:
    lock = BuildLock()
    calls: list[str] = []

    def runner(trigger: str) -> BuildResult:
        calls.append(trigger)
        return _fake_result(trigger)

    result, queued = lock.request("cli", runner)
    assert queued is False
    assert result is not None
    assert result.trigger == "cli"
    assert calls == ["cli"]


def test_pending_merged() -> None:
    lock = BuildLock()
    started = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    def runner(trigger: str) -> BuildResult:
        calls.append(trigger)
        started.set()
        release.wait(timeout=2)
        return _fake_result(trigger)

    def first() -> None:
        lock.request("watch", runner)

    t = threading.Thread(target=first)
    t.start()
    assert started.wait(timeout=2)

    result, queued = lock.request("timer", runner)
    assert queued is True
    assert result is None

    release.set()
    t.join(timeout=2)
    # pending replay should have run
    assert calls == ["watch", "timer"]
    assert lock.building is False
