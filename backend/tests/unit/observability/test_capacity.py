"""007 fail-closed quota proof and exact90% admission boundary, independent of functional resources."""

from types import SimpleNamespace
import json
import pytest
from ecs_ec.observability.capacity import Capacity, QUOTAS


def test_shared_host_filesystem_is_not_a_quota(tmp_path, telemetry_clock):
    """Five directories on one unbounded volume cannot establish five independent budgets."""
    for name in QUOTAS:
        (tmp_path / name).mkdir()
    with pytest.raises(ValueError):
        Capacity(tmp_path, tmp_path / "status.json", "test", "007-v1", telemetry_clock)


@pytest.mark.parametrize("used,allowed", [(89, True), (90, False), (91, False)])
def test_exact_cutoff_and_atomic_numeric_status(
    tmp_path, telemetry_clock, monkeypatch, used, allowed
):
    """A trusted filesystem observation rejects at equality and atomically publishes only safe primitives."""
    from ecs_ec.observability import capacity as module

    for name in QUOTAS:
        (tmp_path / name).mkdir()
    real_stat = module.Path.stat

    def stat(path, *args, **kwargs):
        """Assign distinct synthetic device numbers only to the five fixture sentinels."""
        value = real_stat(path, *args, **kwargs)
        if path.name in QUOTAS:
            return SimpleNamespace(
                st_dev=list(QUOTAS).index(path.name) + 1, st_mode=value.st_mode
            )
        return value

    def usage(path):
        """Return a deterministic byte budget for cutoff tests; no real quota acceptance is claimed."""
        return SimpleNamespace(f_blocks=100, f_frsize=1, f_bavail=100 - used)

    monkeypatch.setattr(module.Path, "stat", stat)
    monkeypatch.setattr(module.os, "statvfs", usage)
    target = tmp_path / "status/status.json"
    capacity = Capacity(tmp_path, target, "test", "007-v1", telemetry_clock)
    assert capacity.observe()["allowed"] is allowed
    snapshot = json.loads(target.read_text())
    assert set(snapshot["quotas"]) == set(QUOTAS)
    assert all(
        set(item) == {"total_bytes", "used_bytes"}
        for item in snapshot["quotas"].values()
    )
    assert snapshot["allowed"] is allowed
