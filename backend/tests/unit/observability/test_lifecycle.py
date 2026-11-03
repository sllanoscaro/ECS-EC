"""Exercise configuration isolation, safe diagnostics, monotonic duration and bounded close."""

import json
import time
from uuid import uuid4
import pytest


def test_invalid_configuration_disables_only_telemetry(tmp_path, capsys):
    """Malformed telemetry settings never abort application setup or print their raw values."""
    from ecs_ec.observability.lifecycle import Telemetry
    telemetry = Telemetry.from_environment({"OBS_ENABLED": "true", "OBS_ENVIRONMENT": "SECRET"})
    assert telemetry.begin("cost.calculate", "costs") is None
    assert telemetry.complete(None) == "disabled"
    assert "SECRET" not in capsys.readouterr().err
    telemetry.shutdown()


def test_operations_duration_context_and_single_terminal(tmp_path, telemetry_clock):
    """An explicit operation handle closes once using monotonic duration; data is schema-valid."""
    from ecs_ec.observability.lifecycle import Telemetry, Policy
    telemetry = Telemetry(Policy(spool=tmp_path, environment="test"), clock=telemetry_clock, autostart=False)
    handle = telemetry.begin("cost.calculate", "costs")
    telemetry_clock.advance(0.2)
    telemetry.stage(handle, "calculate")
    assert telemetry.complete(handle, outcome="success") == "enqueued"
    assert telemetry.complete(handle, outcome="success") == "dropped"
    while telemetry.logs.depth:
        telemetry.logs.drain_one()
    events = [json.loads(line) for p in tmp_path.glob("*.jsonl") for line in p.read_text().splitlines()]
    terminal = [e for e in events if e["event"] == "operation.completed"]
    assert len(terminal) == 1
    assert terminal[0]["duration_ms"] == pytest.approx(200)
    assert terminal[0]["operation_ref"] == str(handle.context.operation_ref)
    assert terminal[0]["trace_id"] is not None
    telemetry.shutdown()


def test_health_control_and_policy_revision(tmp_path, telemetry_clock):
    """Heartbeat has mandatory independent health evidence and emits the active policy revision."""
    from ecs_ec.observability.lifecycle import Telemetry, Policy
    telemetry = Telemetry(Policy(spool=tmp_path, environment="test", revision="r2"), clock=telemetry_clock, autostart=False)
    assert telemetry.health() == "enqueued"
    assert telemetry.logs.depth == 2  # policy.changed data plus replaceable heartbeat
    while telemetry.logs.depth:
        telemetry.logs.drain_one()
    events = [json.loads(line) for p in tmp_path.glob("*.jsonl") for line in p.read_text().splitlines()]
    assert all(e["policy_revision"] == "r2" for e in events)
    assert {e["event"] for e in events} == {"policy.changed", "telemetry.heartbeat"}
    telemetry.shutdown()


def test_heartbeat_worker_uses_fifteen_second_interval(tmp_path, telemetry_clock):
    """Controlled stop token observes the actual worker interval without a slow wall-clock sleep."""
    from ecs_ec.observability.lifecycle import Telemetry, Policy
    telemetry = Telemetry(Policy(spool=tmp_path, environment="test"), clock=telemetry_clock, autostart=False)
    original_health = telemetry.health
    def delayed_health():
        """Simulate one second of health work without extending the15s cadence."""
        result = original_health()
        telemetry_clock.advance(1)
        return result
    telemetry.health = delayed_health
    class Stop:
        """Stop after the first actual heartbeat wait and record its requested duration."""
        stopped = False
        waits = []
        def is_set(self):
            """Report whether the worker has completed its first iteration."""
            return self.stopped
        def wait(self, seconds):
            """Capture the production wait duration and end the controlled loop."""
            self.waits.append(seconds)
            self.stopped = True
    stop = Stop()
    telemetry._stop = stop
    telemetry._heartbeat_loop()
    assert stop.waits == [14]
    assert telemetry.logs.depth == 2
    telemetry.logs.shutdown(0)
    telemetry.traces.shutdown(0)


def test_unregistered_or_untyped_calls_do_not_escape(tmp_path):
    """Unknown producer input is safely rejected without business exception or secret formatting."""
    from ecs_ec.observability.lifecycle import Telemetry, Policy
    telemetry = Telemetry(Policy(spool=tmp_path, environment="test"), autostart=False)
    assert telemetry.begin({}, "costs") is None
    assert telemetry.begin("cost.query", {}) is None
    handle = telemetry.begin("cost.query", "costs")
    assert telemetry.stage(handle, {}) == "dropped"
    assert telemetry.stage(handle, "SECRET") == "dropped"
    assert telemetry.complete(handle, outcome={}) == "dropped"
    assert telemetry.complete(handle, code=object()) == "dropped"
    assert telemetry.complete(object()) == "dropped"
    assert telemetry.stage(object(), "read") == "dropped"
    assert telemetry.complete(handle) == "enqueued"
    telemetry.shutdown()
