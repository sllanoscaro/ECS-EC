"""Create or validate local/test TLS material outside the repo; never print private data.

Inputs: --environment local|test, optional --root absolute external parent. Outputs:
one atomic environment directory containing CA/server and distinct process certificates.
Errors fail closed without replacing existing material. No functional identity is read.
Requires OpenSSL. CA validity 365 days, leaf validity 30 days; renewal is explicit.
"""

import argparse
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def openssl(*arguments):
    """Execute OpenSSL without exposing its output/keys; raise only a fixed safe error."""
    result = subprocess.run(["openssl", *map(str, arguments)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode:
        raise ValueError("TLS material validation or generation failed")


def validate(directory):
    """Reject missing, symlinked, broadly readable or expired material, without mutation."""
    for name in ("ca", "server", "app", "alloy", "health"):
        for suffix in ("key", "crt"):
            path = directory / f"{name}.{suffix}"
            if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
                raise ValueError("TLS files must be private regular files")
        openssl("x509", "-in", directory / f"{name}.crt", "-checkend", "86400", "-noout")
        openssl("verify", "-x509_strict", "-CAfile", directory / "ca.crt", directory / f"{name}.crt")
        key = subprocess.check_output(["openssl", "pkey", "-in", str(directory / f"{name}.key"), "-pubout"], stderr=subprocess.DEVNULL)
        cert = subprocess.check_output(["openssl", "x509", "-in", str(directory / f"{name}.crt"), "-pubkey", "-noout"], stderr=subprocess.DEVNULL)
        if key != cert:
            raise ValueError("Certificate key mismatch")


def prepare(environment, root):
    """Atomically prepare exclusive per-environment material, or validate safe reuse.

    Reject repo descendants and symlink parents before any key creation. Use a local
    exclusive lock; an interrupted generation leaves only a removable private tempdir.
    Existing invalid material is never automatically overwritten or rotated.
    """
    repo = Path(__file__).resolve().parents[2]
    if not root.is_absolute() or root.is_relative_to(repo) or root.resolve().is_relative_to(repo):
        raise ValueError("Choose an absolute directory outside the repository")
    for parent in (root, *root.parents):
        if parent.is_symlink():
            raise ValueError("Symlink resource paths are not supported")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError("Resource root must be owned by the caller with mode 0700")
    with (root / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        destination = root / environment
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or destination.stat().st_mode & 0o077:
                raise ValueError("Environment directory must be private")
            validate(destination)
            return destination
        staging = Path(tempfile.mkdtemp(prefix=f".{environment}-", dir=root))
        try:
            openssl("req", "-x509", "-newkey", "rsa:3072", "-nodes", "-days", "365", "-subj", f"/CN=ecs-obs-{environment}-ca",
                    "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign",
                    "-keyout", staging / "ca.key", "-out", staging / "ca.crt")
            for name in ("server", "app", "alloy", "health"):
                extension = staging / "extension.cnf"
                extension.write_text("basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=" +
                                     ("serverAuth\nsubjectAltName=DNS:localhost,DNS:technical-gateway,IP:127.0.0.1\n" if name == "server" else "clientAuth\n"))
                openssl("req", "-new", "-newkey", "rsa:3072", "-nodes", "-subj", f"/CN=ecs-obs-{environment}-{name}",
                        "-keyout", staging / f"{name}.key", "-out", staging / f"{name}.csr")
                openssl("x509", "-req", "-in", staging / f"{name}.csr", "-CA", staging / "ca.crt", "-CAkey", staging / "ca.key",
                        "-CAcreateserial", "-days", "30", "-extfile", extension, "-out", staging / f"{name}.crt")
            for file in staging.iterdir():
                if file.suffix not in {".crt", ".key"}:
                    file.unlink()
                else:
                    file.chmod(0o600)
            for name in ("credentials", "spool"):
                (staging / name).mkdir(mode=0o700)
            (staging / "environment").write_text(environment + "\n")
            (staging / "environment").chmod(0o600)
            validate(staging)
            staging.rename(destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        return destination


def process_material(directory):
    """Publish separate private mounts per process, excluding CA key and other client keys.

    Safe repeat verifies byte equality; mismatched existing files fail without overwrite.
    Data directories remain separate from credentials and functional persistence.
    """
    import shutil
    for name, leaf in (("gateway", "server"), ("app", "app"), ("alloy", "alloy"), ("health", "health")):
        target = directory / "clients" / name
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        for source in ("ca.crt", leaf + ".crt", leaf + ".key"):
            output = target / source
            if output.is_symlink() or output.exists() and output.read_bytes() != (directory / source).read_bytes():
                raise ValueError("Process mount differs from prepared TLS material")
            if not output.exists():
                shutil.copyfile(directory / source, output)
                output.chmod(0o600)
    for name in ("alloy", "loki", "jaeger", "grafana"):
        target = directory / "data" / name
        target.mkdir(parents=True, exist_ok=True, mode=0o700)


def main():
    """Parse safe CLI inputs; print only the prepared public path or a fixed diagnostic."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("local", "test"), required=True)
    parser.add_argument("--root", type=Path, default=Path.home() / ".local/state/ecs-ec/observability")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        directory = prepare(args.environment, args.root)
        process_material(directory)
        print(directory)
    except (ValueError, OSError, subprocess.SubprocessError):
        parser.exit(1, "Technical TLS preparation failed; check private paths, permissions and certificates.\n")


if __name__ == "__main__":
    main()
