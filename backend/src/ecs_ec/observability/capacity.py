"""007 fixed-filesystem quota observation in the monolith's existing technical worker.

Only empty sentinel mounts are visible here, never Loki/Badger/Grafana contents.
A bounded atomic snapshot lets the mTLS gateway reject ingestion at90% or on stale
proof. Functional calls neither read this state nor wait on disk/network.
"""

import json
import os
from pathlib import Path
import tempfile

QUOTAS = {
    "spool": 128 * 1024**2,
    "alloy": 64 * 1024**2,
    "loki": 2 * 1024**3,
    "jaeger": 2 * 1024**3,
    "grafana": 256 * 1024**2,
}


class Capacity:
    """Observe separate fixed filesystems and publish only size/usage/UTC policy primitives."""

    def __init__(self, root, status, environment, revision, clock):
        """Validate sentinel paths before activation; invalid physical bounds disable only technical emission."""
        self.root, self.status = Path(root), Path(status)
        self.environment, self.revision, self.clock = environment, revision, clock
        snapshot = self.snapshot()
        if not snapshot["valid"]:
            raise ValueError("Invalid technical quota mounts")

    def snapshot(self):
        """Return a bounded fail-closed snapshot; shared/oversized/missing filesystems cannot prove a quota."""
        quotas = {}
        devices = set()
        valid = True
        for name, ceiling in QUOTAS.items():
            path = self.root / name
            try:
                if path.is_symlink() or not path.is_dir():
                    raise ValueError()
                stat = os.statvfs(path)
                device = path.stat().st_dev
                total = stat.f_blocks * stat.f_frsize
                # Reserved blocks are unavailable to the unprivileged writers and
                # count against their budget; filesystem overhead is reported separately.
                used = total - stat.f_bavail * stat.f_frsize
                if (
                    device in devices
                    or not 0 < total <= ceiling
                    or not 0 <= used <= total
                ):
                    raise ValueError()
                devices.add(device)
                quotas[name] = {"total_bytes": total, "used_bytes": used}
            except OSError, ValueError:
                valid = False
        return dict(
            environment=self.environment,
            policy_revision=self.revision,
            timestamp=self.clock.now().isoformat().replace("+00:00", "Z"),
            valid=valid,
            allowed=valid
            and all(
                item["used_bytes"] * 10 < item["total_bytes"] * 9
                for item in quotas.values()
            ),
            quotas=quotas,
        )

    def observe(self):
        """Atomically update the gateway's directory mount from the technical worker; failures leave stale denial."""
        temporary = None
        try:
            snapshot = self.snapshot()
            self.status.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.NamedTemporaryFile(
                mode="w", dir=self.status.parent, prefix=".quota-", delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(snapshot, stream, separators=(",", ":"), allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o600)
            temporary.replace(self.status)
            return snapshot
        except OSError, ValueError:
            return None
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
