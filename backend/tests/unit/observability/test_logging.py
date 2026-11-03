"""Admission, bounded queue, immutable spool and safe failures independent of domain results."""

import json
import threading
import time


def test_capacity_and_replaceable_control(safe_event, tmp_path):
    """1023 data events plus one replaceable control never block or exceed1024 slots."""
    from ecs_ec.observability.logging import LogEmitter
    log = LogEmitter(tmp_path, autostart=False)
    for _ in range(1023):
        assert log.emit(safe_event) == "enqueued"
    assert log.emit(safe_event) == "dropped"
    assert log.emit(safe_event, control=True) == "enqueued"
    assert log.emit(safe_event, control=True) == "enqueued"
    assert log.depth == 1024
    assert log.dropped == 2
    log.shutdown(0)
    assert log.depth == 0
    assert log.dropped == 1026


def test_sequence_holes_and_immutable_body(safe_event, tmp_path):
    """Validation failures leave sequence gaps; worker writes the original admitted bytes."""
    from ecs_ec.observability.logging import LogEmitter
    log = LogEmitter(tmp_path, autostart=False)
    assert log.emit(safe_event) == "enqueued"
    safe_event["body"] = "SECRET"
    assert log.emit(safe_event) == "dropped"
    del safe_event["body"]
    assert log.emit(safe_event) == "enqueued"
    log.drain_one()
    log.drain_one()
    events = [json.loads(row) for row in (tmp_path / "events-0.jsonl").read_text().splitlines()]
    assert [event["sequence"] for event in events] == [1, 3]
    assert "SECRET" not in json.dumps(events)
    assert log.schema_rejected == 1


def test_rotation_ttl_and_disk_failure(safe_event, tmp_path, telemetry_clock):
    """Spool respects explicit test limits and expires only technical files; disk errors count."""
    from ecs_ec.observability.logging import LogEmitter
    log = LogEmitter(tmp_path, autostart=False, file_bytes=2000, files=2, ttl_seconds=60, clock=telemetry_clock)
    for _ in range(10):
        log.emit(safe_event)
        log.drain_one()
    assert len(list(tmp_path.glob("events-*.jsonl"))) <= 2
    assert sum(p.stat().st_size for p in tmp_path.glob("events-*.jsonl")) <= 4000
    assert log.spool_dropped > 0
    telemetry_clock.advance(61)
    log.expire()
    assert not list(tmp_path.glob("events-*.jsonl"))
    broken = tmp_path / "file"
    broken.write_text("occupied")
    other = LogEmitter(broken, autostart=False)
    assert other.emit(safe_event) == "enqueued"
    other.drain_one()
    assert other.spool_dropped == 1


def test_admission_does_not_wait_for_sink(safe_event, tmp_path):
    """A blocked disk worker never holds admission; shutdown has a real shared deadline."""
    from ecs_ec.observability.logging import LogEmitter
    entered, release = threading.Event(), threading.Event()
    def stalled_write(data):
        """Model an unavailable sink; only this worker waits, never the caller."""
        entered.set()
        release.wait(2)
    log = LogEmitter(tmp_path, writer=stalled_write)
    log.emit(safe_event)
    assert entered.wait(1)
    start = time.monotonic()
    for _ in range(1500):
        log.emit(safe_event)
    # A generous total bound detects waiting for the stalled sink, not a throughput SLO.
    assert time.monotonic() - start < 1.5
    start = time.monotonic()
    log.shutdown(0.05)
    assert time.monotonic() - start < 0.5
    release.set()
    assert log.dropped > 0
