"""Allocate/mount only new007 fixed ext4 images outside the repo; unmount by verified backing file.

Linux host operator command. Mounts use a disposable root Docker process with the host
mount namespace; no network, Docker socket, functional paths or wildcard mount operations.
All target directories must be empty. Images remain after unmount for persistence.
Never use this command on existing nonempty service directories or a functional volume.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess

from ecs_ec.observability.capacity import QUOTAS


TARGETS = {
    "spool": "spool",
    "alloy": "data/alloy",
    "loki": "data/loki",
    "jaeger": "data/jaeger",
    "grafana": "data/grafana",
}


def host(image, *arguments):
    """Run a structured bounded host command; root privileges have no network or interpolated shell text."""
    return subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--user",
            "0",
            "--privileged",
            "--pid=host",
            "--network",
            "none",
            image,
            "/usr/bin/nsenter",
            "--target",
            "1",
            "--mount",
            "--root=/proc/1/root",
            "--wd=/proc/1/root",
            "--",
            *map(str, arguments),
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=True,
    )


def checked(root):
    """Require a real owned prepared test/local root outside the repo before any filesystem operation."""
    repo = Path(__file__).resolve().parents[2]
    if (
        not root.is_absolute()
        or root.resolve().is_relative_to(repo)
        or any(path.is_symlink() for path in (root, *root.parents))
    ):
        raise ValueError("External real path required")
    if (
        root.stat().st_uid != os.getuid()
        or root.stat().st_mode & 0o077
        or (root / "environment").read_text().strip() not in {"test", "local"}
    ):
        raise ValueError("Private prepared root required")
    return root


def mounts(root):
    """Return only exact mountpoints; never fall back from a missing target to the containing host filesystem."""
    result = {}
    for name, target in TARGETS.items():
        probe = subprocess.run(
            [
                "findmnt",
                "--json",
                "--mountpoint",
                str(root / target),
                "--output",
                "TARGET,SOURCE",
            ],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            result[name] = json.loads(probe.stdout)["filesystems"][0]["source"]
    return result


def prepare(root, image):
    """Create sparse bounded ext4 files, mount exclusively and expose empty read-only capacity sentinels."""
    checked(root)
    images = root / "quota-images"
    manifest = root / "quota-manifest.json"
    if images.exists() or manifest.exists() or mounts(root):
        raise ValueError("Quota resources already exist; do not overwrite")
    for target in TARGETS.values():
        path = root / target
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Unsafe target path")
        if path.exists() and any(path.iterdir()):
            raise ValueError("Target must be empty")
    images.mkdir(mode=0o700)
    record = {"owner_uid": os.getuid(), "root": str(root), "images": {}, "mounted": []}
    manifest.write_text(json.dumps(record))
    manifest.chmod(0o600)
    try:
        for name, ceiling in QUOTAS.items():
            disk = images / (name + ".ext4")
            target = root / TARGETS[name]
            with disk.open("xb") as stream:
                stream.truncate(ceiling)
            disk.chmod(0o600)
            subprocess.run(
                ["/usr/sbin/mkfs.ext4", "-q", "-m", "10", str(disk)],
                check=True,
                capture_output=True,
                timeout=45,
            )
            target.mkdir(parents=True, exist_ok=True, mode=0o700)
            record["images"][name] = str(disk)
            manifest.write_text(json.dumps(record))
            host(
                image,
                "/usr/bin/mount",
                "-t",
                "ext4",
                "-o",
                "loop,nodev,nosuid,noexec",
                disk,
                target,
            )
            record["mounted"].append(name)
            manifest.write_text(json.dumps(record))
            host(image, "/usr/bin/chown", f"{os.getuid()}:{os.getgid()}", target)
            target.chmod(0o700)
            (target / ".capacity").mkdir(mode=0o700)
        (root / "quota-status").mkdir(mode=0o700)
        (root / "quota-status/manifest.json").write_text(
            json.dumps({"schema": 1, "ceilings": QUOTAS})
        )
        (root / "quota-status/manifest.json").chmod(0o600)
        return manifest
    except BaseException:
        # Keep manifest/images for an explicit verified cleanup; never remove or
        # unmount unknown resources after a partial failure.
        raise


def unmount(root, image):
    """Unmount only this caller's recorded images after verifying each actual loop backing file; keep data."""
    checked(root)
    record = json.loads((root / "quota-manifest.json").read_text())
    if record["owner_uid"] != os.getuid() or record["root"] != str(root):
        raise ValueError("Foreign manifest")
    active = mounts(root)
    for name in reversed(list(TARGETS)):
        if name not in active:
            continue
        disk = root / "quota-images" / (name + ".ext4")
        if record["images"].get(name) != str(disk):
            raise ValueError("Unexpected backing image")
        detail = json.loads(
            host(
                image,
                "/usr/sbin/losetup",
                "--json",
                "--list",
                "--output",
                "BACK-FILE",
                active[name],
            ).stdout
        )
        if detail["loopdevices"][0]["back-file"] != str(disk):
            raise ValueError("Foreign mount")
        host(image, "/usr/bin/umount", root / TARGETS[name])
    record["mounted"] = []
    (root / "quota-manifest.json").write_text(json.dumps(record))


def main():
    """Require explicit host-mount intent; print only a fixed result and no credentials/device inventories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "unmount"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--allow-host-mounts", action="store_true", required=True)
    args = parser.parse_args()
    try:
        (prepare if args.action == "prepare" else unmount)(args.root, args.image)
        print("Technical quota " + args.action + " completed")
    except (
        ValueError,
        OSError,
        subprocess.SubprocessError,
        KeyError,
        json.JSONDecodeError,
    ):
        parser.exit(
            1,
            "Technical quota operation failed; retain the manifest and verify only its own paths.\n",
        )


if __name__ == "__main__":
    main()
