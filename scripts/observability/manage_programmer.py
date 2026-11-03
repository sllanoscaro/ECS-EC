"""External per-environment Programador registry and atomic htpasswd authorization.

Inputs: grant|revoke --environment local|test|vps --subject opaque --root external.
No password argument/environment/stdin support; interactive grant reads /dev/tty.
Outputs only revision/result. Registry is operational, never an identity006 account.
Nginx reopens authorized on each request; mounting the directory preserves rename.
"""

import argparse
import fcntl
import getpass
import json
import os
from pathlib import Path
import re
import tempfile

import bcrypt


def atomic_write(path, contents):
    """Replace one private file atomically in its mounted directory; fsync before publication."""
    descriptor, temporary = tempfile.mkstemp(prefix=".provision-", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update(root, environment, subject, action, password=None):
    """Validate external resource/state, hash or revoke, atomically publish authorization.

    Password bytes are an internal TTY/test seam, never CLI arguments. Lock serializes
    operators. Failures before publication preserve old authorization; revoke first
    publishes a denying file, then registry. Interrupted state mismatches fail closed
    on next operation and require explicit host recovery, never silent regrant.
    """
    if environment not in {"local", "test", "vps"} or action not in {"grant", "revoke"}:
        raise ValueError("Invalid provisioning request")
    if type(subject) is not str or not re.fullmatch(r"prog-[a-z0-9][a-z0-9-]{2,47}", subject):
        raise ValueError("Opaque subject required")
    root = Path(root)
    repo = Path(__file__).resolve().parents[2]
    if not root.is_absolute() or root.resolve().is_relative_to(repo):
        raise ValueError("External root required")
    directory = root / environment
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError("Symlink resource path rejected")
    if not directory.is_dir() or directory.stat().st_uid != os.getuid() or directory.stat().st_mode & 0o077:
        raise ValueError("Prepared private environment required")
    if (directory / "environment").read_text().strip() != environment:
        raise ValueError("Environment mismatch")
    credentials = directory / "credentials"
    credentials.mkdir(mode=0o700, exist_ok=True)
    if credentials.is_symlink() or credentials.stat().st_mode & 0o077:
        raise ValueError("Private credential directory required")
    with (credentials / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        registry_path, authorization = credentials / "registry.json", credentials / "authorized"
        if any(path.is_symlink() for path in (registry_path, authorization)):
            raise ValueError("Private regular credential files required")
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"environment": environment, "revision": 0, "subjects": {}}
        if registry["environment"] != environment:
            raise ValueError("Environment mismatch")
        expected = render(registry)
        if authorization.exists() and authorization.read_bytes() != expected:
            raise ValueError("Authorization/registry mismatch; host recovery required")
        if not authorization.exists() and registry["revision"]:
            raise ValueError("Missing authorization file; host recovery required")
        subjects = registry["subjects"]
        if action == "grant":
            if type(password) is not bytes or not 16 <= len(password) <= 72:
                raise ValueError("Password must contain16–72UTF8 bytes")
            verifier = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12)).decode("ascii")
            if not bcrypt.checkpw(password, verifier.encode("ascii")):
                raise ValueError("Verifier self-check failed")
            subjects[subject] = {"state": "enabled", "verifier": verifier}
        else:
            subjects[subject] = {"state": "revoked", "verifier": None}
        registry["revision"] += 1
        # Two files cannot be atomically renamed together. For grant, persist registry
        # first (old auth keeps its current permissions); for revoke, deny immediately.
        new_authorization = render(registry)
        if action == "grant":
            atomic_write(registry_path, json.dumps(registry, sort_keys=True).encode())
            atomic_write(authorization, new_authorization)
        else:
            atomic_write(authorization, new_authorization)
            atomic_write(registry_path, json.dumps(registry, sort_keys=True).encode())
        descriptor = os.open(credentials, os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return registry["revision"]


def render(registry):
    """Generate constrained htpasswd lines only from validated opaque subjects/bcrypt verifiers."""
    lines = []
    for subject, entry in sorted(registry["subjects"].items()):
        if not re.fullmatch(r"prog-[a-z0-9][a-z0-9-]{2,47}", subject) or entry["state"] not in {"enabled", "revoked"}:
            raise ValueError("Invalid registry")
        if entry["state"] == "enabled":
            verifier = entry["verifier"]
            if type(verifier) is not str or not re.fullmatch(r"\$2b\$12\$[./A-Za-z0-9]{53}", verifier):
                raise ValueError("Invalid registry verifier")
            lines.append(subject + ":" + verifier + "\n")
    return "".join(lines).encode("ascii")


def main():
    """Read interactive password only from controlling TTY and emit no subject/verifier/private input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("grant", "revoke"))
    parser.add_argument("--environment", choices=("local", "test", "vps"), required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--root", type=Path, default=Path.home() / ".local/state/ecs-ec/observability")
    # Argument errors must not echo unknown arguments, which could accidentally be a password.
    try:
        args, unknown = parser.parse_known_args()
        if unknown:
            parser.exit(2, "Unknown provisioning argument.\n")
        os.umask(0o077)
        password = None
        if args.action == "grant":
            with open("/dev/tty", "w") as tty:
                first = getpass.getpass("Technical password: ", stream=tty)
                second = getpass.getpass("Repeat technical password: ", stream=tty)
            if first != second:
                raise ValueError()
            password = first.encode("utf-8")
        revision = update(args.root, args.environment, args.subject, args.action, password)
        print(f"revision={revision} result={args.action}")
    except (ValueError, OSError, KeyError, TypeError):
        parser.exit(1, "Technical provisioning failed; check private resource state and TTY.\n")


if __name__ == "__main__":
    main()
