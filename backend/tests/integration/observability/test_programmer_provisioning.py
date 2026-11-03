"""External identity state/atomicity tests; real Nginx crypt interoperability is checked by access suite."""

import json
import os
import stat
import bcrypt
import pytest


def test_grant_revoke_and_explicit_regrant(tmp_path):
    """Each state transition advances revision and atomically changes the mounted directory file."""
    from scripts.observability.manage_programmer import update
    root = tmp_path / "external"
    root.mkdir(mode=0o700)
    environment = root / "test"
    environment.mkdir(mode=0o700)
    (environment / "environment").write_text("test\n")
    password = b"Synthetic technical password 007"
    update(root, "test", "prog-test-01", "grant", password)
    file = environment / "credentials/authorized"
    before = file.stat().st_ino
    subject, hashed = file.read_bytes().strip().split(b":", 1)
    assert subject == b"prog-test-01"
    assert bcrypt.checkpw(password, hashed)
    assert stat.S_IMODE(file.stat().st_mode) == 0o600
    assert password not in file.read_bytes()
    update(root, "test", "prog-test-01", "revoke")
    assert file.stat().st_ino != before
    assert file.read_bytes() == b""
    registry = json.loads((environment / "credentials/registry.json").read_text())
    assert registry["revision"] == 2
    assert registry["subjects"]["prog-test-01"]["state"] == "revoked"
    assert registry["subjects"]["prog-test-01"]["verifier"] is None
    update(root, "test", "prog-test-01", "grant", password)
    assert file.read_bytes().startswith(b"prog-test-01:$2b$")
    assert not (root / "local").exists()


@pytest.mark.parametrize("subject", ["alice@example.test", "../prog-test-01", "prog-x\nOTHER:hash", "admin", "prog-a:hash"])
def test_reject_personal_or_injectable_subject(tmp_path, subject):
    """Only opaque constrained subjects can enter htpasswd; reject injection before mutation."""
    from scripts.observability.manage_programmer import update
    with pytest.raises(ValueError):
        update(tmp_path, "test", subject, "grant", b"Synthetic password 007")
    assert not list(tmp_path.iterdir())


def test_cli_has_no_password_argument_and_requires_tty(tmp_path):
    """A noninteractive grant cannot obtain credentials from stdin, arguments or environment."""
    import subprocess
    command = ["bash", "scripts/observability/manage_programmer.sh", "grant", "--environment", "test", "--subject", "prog-test-01", "--root", str(tmp_path)]
    result = subprocess.run(command, input=b"Synthetic password 007\n", capture_output=True)
    assert result.returncode != 0
    assert b"Synthetic password" not in result.stdout + result.stderr
    result = subprocess.run(command + ["--password", "Synthetic password 007"], capture_output=True)
    assert result.returncode != 0
    assert b"Synthetic password" not in result.stdout + result.stderr


def test_actual_cli_grant_over_controlling_tty(gateway_root):
    """A real PTY can provision without echo or argv/stdout secrets; revoked test subject is cleaned up."""
    import errno
    import pty
    import select
    import time
    from scripts.observability.manage_programmer import update
    pid, descriptor = pty.fork()
    if pid == 0:
        os.execvp("bash", ["bash", "scripts/observability/manage_programmer.sh", "grant", "--environment", "test",
                           "--subject", "prog-tty-01", "--root", str(gateway_root.parent)])
    transcript = b""
    sent = 0
    status = None
    deadline = time.monotonic() + 10
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([descriptor], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(descriptor, 4096)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                transcript += chunk
                if sent == 0 and b"Technical password:" in transcript:
                    os.write(descriptor, b"Synthetic TTY password 007\n")
                    sent = 1
                elif sent == 1 and b"Repeat technical password:" in transcript:
                    os.write(descriptor, b"Synthetic TTY password 007\n")
                    sent = 2
            found, polled_status = os.waitpid(pid, os.WNOHANG)
            if found:
                status = polled_status
                break
        if status is None:
            found, polled_status = os.waitpid(pid, os.WNOHANG)
            if not found:
                os.kill(pid, 15)
                _, polled_status = os.waitpid(pid, 0)
            status = polled_status
        assert os.waitstatus_to_exitcode(status) == 0
        assert sent == 2
        assert b"Synthetic TTY password" not in transcript
        assert b"result=grant" in transcript
        assert b"prog-tty-01:" in (gateway_root / "credentials/authorized").read_bytes()
    finally:
        os.close(descriptor)
        if status is None:
            try:
                os.kill(pid, 15)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
        update(gateway_root.parent, "test", "prog-tty-01", "revoke")
