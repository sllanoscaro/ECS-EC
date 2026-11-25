"""007 resumable24h real-time retention probe on an exclusively prepared test quota stack.

The host operator owns Docker lifecycle; Programador requests still use trusted CA
and Basic on every read. Credentials are read from a private file and never persisted
in results or argv. This script records evidence; it never marks Spec Kit tasks or
claims physical Badger removal from a404. No functional volume is mounted or changed.
"""

import argparse
from datetime import UTC, datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import ssl
import subprocess
import tempfile
import time

import httpx

from ecs_ec.observability.queries import metric_query

STATE = "retention-probe.json"


def now():
    """Return real UTC; no controllable application clock is used by the prolonged probe."""
    return datetime.now(UTC)


def stamp(value):
    """Serialize an actual UTC observation with an explicit Z suffix."""
    return value.isoformat().replace("+00:00", "Z")


def save(root, state):
    """Atomically replace only the private owned probe result, preserving interrupted-run evidence."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=root, prefix=".retention-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        temporary.replace(root / STATE)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def validate(root, project, password_file):
    """Reject foreign, symlinked, non-test or unowned material before queries or lifecycle changes."""
    if (
        not root.is_absolute()
        or root.name != "test"
        or root.is_symlink()
        or root.resolve() != root
    ):
        raise ValueError()
    if root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError()
    manifest = json.loads((root / "quota-manifest.json").read_text())
    if (
        (root / "environment").read_text().strip() != "test"
        or manifest["root"] != str(root)
        or manifest["owner_uid"] != os.getuid()
    ):
        raise ValueError()
    if not re.fullmatch(r"ecs007-[a-z0-9-]+", project):
        raise ValueError()
    if (
        not password_file.is_absolute()
        or password_file.is_symlink()
        or password_file.stat().st_uid != os.getuid()
        or password_file.stat().st_mode & 0o077
    ):
        raise ValueError()
    if not 1 <= password_file.stat().st_size <= 1024:
        raise ValueError()


def owned_container(root, project, service):
    """Require the exact isolated source mount before controlling a test service; never inspect secret values in output."""
    if service not in {"loki", "jaeger", "worker"}:
        raise ValueError()
    name = project + "-" + service + ("" if service == "worker" else "-1")
    metadata = json.loads(subprocess.check_output(["docker", "inspect", name]))[0]
    source = str(root / ("spool" if service == "worker" else "data/" + service))
    if not any(mount.get("Source") == source for mount in metadata["Mounts"]):
        raise ValueError()
    return name


def storage(root):
    """Record bounded physical allocation and relative technical file paths; never read secrets or payload bytes."""
    result = {}
    for name, path in [
        ("logs", root / "data/loki/chunks"),
        ("traces", root / "data/jaeger"),
        ("spool", root / "spool"),
    ]:
        files = []
        truncated = False
        for file in path.rglob("*"):
            if file.is_symlink():
                raise ValueError()
            if not file.is_file():
                continue
            stat = file.stat()
            files.append(
                {
                    "path": str(file.relative_to(path)),
                    "size": stat.st_size,
                    "allocated": stat.st_blocks * 512,
                    "mtime": stat.st_mtime,
                }
            )
            if len(files) >= 20000:
                truncated = True
                break
        result[name] = {
            "files": files,
            "truncated": truncated,
            "allocated": sum(file["allocated"] for file in files),
        }
    return result


def readings(root, state):
    """Query the original finite window under current Basic authorization; unavailable never means absent."""
    password = Path(state["password_file"]).read_text().strip()
    tls = ssl.create_default_context(cafile=str(root / "ca.crt"))
    with httpx.Client(
        base_url=state["url"],
        verify=tls,
        auth=("prog-test-01", password),
        trust_env=False,
        timeout=30,
    ) as client:
        response = client.get(
            "/logs/loki/api/v1/query_range",
            params={
                "query": '{service_name="ecs-ec",environment="test",operation="consumption.query_detail"}',
                "start": str(state["start_ns"]),
                "end": str(state["end_ns"] - 1),
                "limit": 10000,
            },
        )
        response.raise_for_status()
        rows = [
            json.loads(line)
            for stream in response.json()["data"]["result"]
            for _, line in stream["values"]
        ]
        expected = {item["operation_ref"] for item in state["fixture"]["references"]}
        found = {
            row["operation_ref"]
            for row in rows
            if row["event"] == "operation.completed"
            and row["operation_ref"] in expected
        }
        measure = client.get(
            "/logs/loki/api/v1/query",
            params={
                "query": metric_query(
                    "operations_total",
                    "test",
                    "consumption.query_detail",
                    state["window_ms"],
                ),
                "time": str(state["end_ns"] - 1),
            },
        )
        measure.raise_for_status()
        vectors = measure.json()["data"]["result"]
        count = float(vectors[0]["value"][1]) if vectors else None
        statuses = []
        for item in state["fixture"]["references"]:
            trace = client.get("/jaeger/api/v3/traces/" + item["trace_id"])
            if trace.status_code not in {200, 404}:
                trace.raise_for_status()
            statuses.append(trace.status_code)
    return {
        "observed_at": stamp(now()),
        "logs": len(found),
        "metric_operations": count,
        "traces": statuses,
        "storage": storage(root),
    }


def start(root, project, image, url, password_file):
    """Emit a technical fixture, prove three signals across restart, keep only the existing heartbeat/TTL worker running."""
    validate(root, project, password_file)
    if (root / STATE).exists():
        raise ValueError()
    if not re.fullmatch(r"https://localhost:[0-9]{4,5}", url):
        raise ValueError()
    producer = owned_container(root, project, "worker")
    services = [owned_container(root, project, name) for name in ("loki", "jaeger")]
    state = {
        "phase": "preparing",
        "project": project,
        "url": url,
        "password_file": str(password_file),
        "started_at": stamp(now()),
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "boottime_start": time.clock_gettime(time.CLOCK_BOOTTIME),
        "observations": [],
    }
    save(root, state)
    try:
        source = Path(__file__).with_name("emit_reference.py").read_text()
        result = subprocess.run(
            ["docker", "exec", "-i", producer, "/app/.venv/bin/python", "-"],
            input=source,
            capture_output=True,
            text=True,
            check=True,
            timeout=40,
        )
        fixture = json.loads(result.stdout)
        state["fixture"] = fixture
        begin = datetime.fromisoformat(fixture["start"]).timestamp()
        end = datetime.fromisoformat(fixture["cutoff"]).timestamp()
        state.update(
            start_ns=math.floor(begin * 1000) * 1000000,
            end_ns=(math.ceil(end * 1000) + 1) * 1000000,
        )
        state["window_ms"] = (state["end_ns"] - state["start_ns"]) // 1000000
        state["before_restart"] = readings(root, state)
        assert (
            state["before_restart"]["logs"] == 10
            and state["before_restart"]["metric_operations"] == 10
            and state["before_restart"]["traces"] == [200] * 10
        )
        code = "import httpx; r=httpx.post('http://127.0.0.1:3100/flush',timeout=20);r.raise_for_status()"
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "container:" + services[0],
                image,
                "/app/.venv/bin/python",
                "-c",
                code,
            ],
            capture_output=True,
            check=True,
            timeout=25,
        )
        subprocess.run(
            ["docker", "restart", *services],
            capture_output=True,
            check=True,
            timeout=40,
        )
        for _ in range(40):
            try:
                after = readings(root, state)
                if (
                    after["logs"] == 10
                    and after["metric_operations"] == 10
                    and after["traces"] == [200] * 10
                ):
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        else:
            raise ValueError()
        state["after_restart"] = after
        state["physical_baseline"] = storage(root)
        first = datetime.fromisoformat(fixture["start"])
        # Track original spool segments independently: continuing control events
        # must not renew them, and older control segments do not shorten the
        # separate24h cohort's Loki/Jaeger verification budget.
        state["spool_sources"] = []
        for path in (root / "spool").glob("events-*.jsonl"):
            with path.open("rb") as stream:
                line = stream.readline(16385)
            try:
                event = json.loads(line)
                original = datetime.fromisoformat(event["timestamp"])
                state["spool_sources"].append(
                    {
                        "path": path.name,
                        "first_event_id": event["event_id"],
                        "first_timestamp": stamp(original),
                        "verification_deadline": stamp(original + timedelta(hours=25)),
                    }
                )
            except ValueError, KeyError, TypeError:
                pass
        state["oldest_source_at"] = stamp(first)
        last = datetime.fromisoformat(fixture["cutoff"])
        state.update(
            phase="waiting_real_ttl",
            precheck_at=stamp(first + timedelta(hours=23, minutes=50)),
            expires_at=stamp(last + timedelta(hours=24, seconds=10)),
            verification_deadline=stamp(first + timedelta(hours=25)),
        )
        save(root, state)
        return state
    except BaseException:
        state["phase"] = "setup_failed"
        save(root, state)
        raise


def run(root):
    """Wait on actual elapsed time and collect post-TTL evidence; physical deletion always requires review."""
    state = json.loads((root / STATE).read_text())
    validate(root, state["project"], Path(state["password_file"]))
    if state["phase"] not in {"waiting_real_ttl", "observing_expiration"}:
        raise ValueError()
    if Path("/proc/sys/kernel/random/boot_id").read_text().strip() != state["boot_id"]:
        state["phase"] = "boot_changed_elapsed_time_unverified"
        save(root, state)
        return
    expiry = datetime.fromisoformat(state["expires_at"])
    deadline = datetime.fromisoformat(state["verification_deadline"])
    while now() < deadline:
        current = now()
        elapsed = time.clock_gettime(time.CLOCK_BOOTTIME) - state["boottime_start"]
        for segment in state.get("spool_sources", []):
            if "checked_at" in segment:
                continue
            due = datetime.fromisoformat(segment["first_timestamp"]) + timedelta(
                hours=24, minutes=1
            )
            if current >= due:
                segment["checked_at"] = stamp(current)
                path = root / "spool" / segment["path"]
                segment["physically_removed"] = not path.exists()
                if path.exists():
                    # Rotating segment names are reused after unlink. Compare
                    # the immutable first event rather than requiring that its
                    # pathname remain absent while new heartbeats continue.
                    with path.open("rb") as stream:
                        replacement = json.loads(stream.readline(16385))
                    segment["physically_removed"] = (
                        replacement["event_id"] != segment["first_event_id"]
                    )
                    segment["current_first_timestamp"] = replacement["timestamp"]
                segment["within_verification_budget"] = (
                    current <= datetime.fromisoformat(segment["verification_deadline"])
                )
                save(root, state)
        if (
            current >= datetime.fromisoformat(state["precheck_at"])
            and "pre_ttl" not in state
        ):
            try:
                state["pre_ttl"] = readings(root, state)
            except httpx.HTTPError:
                state["pre_ttl_query_failed"] = stamp(current)
            save(root, state)
        if current >= expiry and elapsed >= 86400:
            state["phase"] = "observing_expiration"
            try:
                observation = readings(root, state)
                state["observations"].append(observation)
                if (
                    observation["logs"] == 0
                    and observation["metric_operations"] is None
                    and observation["traces"] == [404] * 10
                ):
                    state["phase"] = "expired_query_confirmed_physical_review_pending"
                    before = {
                        file["path"]
                        for file in state["physical_baseline"]["logs"]["files"]
                    }
                    after = {
                        file["path"] for file in observation["storage"]["logs"]["files"]
                    }
                    state["loki_original_files_removed"] = bool(
                        before
                    ) and not before.intersection(after)
                    state["physical_badger_accepted"] = False
                    save(root, state)
                    return
            except httpx.HTTPError:
                state["last_query_failure"] = stamp(current)
            save(root, state)
            time.sleep(min(60, max(0, (deadline - now()).total_seconds())))
        else:
            time.sleep(min(60, max(1, (expiry - current).total_seconds())))
    state["phase"] = "verification_deadline_missed_or_retention_failed"
    save(root, state)


def main():
    """Expose explicit start/run/status commands; errors contain a fixed code, never credentials or server bodies."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "run", "status"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--project")
    parser.add_argument("--image")
    parser.add_argument("--url")
    parser.add_argument("--password-file", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "start":
            state = start(
                args.root, args.project, args.image, args.url, args.password_file
            )
        elif args.action == "run":
            run(args.root)
            state = json.loads((args.root / STATE).read_text())
        else:
            state = json.loads((args.root / STATE).read_text())
        print(
            json.dumps(
                {
                    key: state.get(key)
                    for key in (
                        "phase",
                        "started_at",
                        "expires_at",
                        "verification_deadline",
                        "loki_original_files_removed",
                    )
                }
            )
        )
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        AssertionError,
        subprocess.SubprocessError,
        httpx.HTTPError,
    ):
        parser.exit(
            1,
            "Retention probe failed; inspect the owned private state without publishing credentials.\n",
        )


if __name__ == "__main__":
    main()
