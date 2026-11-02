"""CLI credentials require TTY and never accept or reflect password arguments."""

import io
import subprocess

import pytest

from ecs_ec.cli import read_password
from ecs_ec.identity.errors import IdentityProblem


def test_non_tty_rejected(monkeypatch):
    """Piped ordinary stdin is never treated as an operational bootstrap password channel."""
    monkeypatch.setattr("sys.stdin", io.StringIO("Synthetic password 006"))
    with pytest.raises(IdentityProblem):
        read_password()


def test_exact_password_getpass_twice(monkeypatch):
    """The protected prompt preserves whitespace and verifies confirmation without printing values."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stderr.isatty", lambda: True)
    prompts = []

    def prompt(label):
        """Record prompt names only, returning an exact synthetic value."""
        prompts.append(label)
        return "  Synthetic password 006  "

    monkeypatch.setattr("getpass.getpass", prompt)
    assert read_password() == "  Synthetic password 006  "
    assert len(prompts) == 2


def test_password_option_is_never_reflected():
    """An accidental unsupported password flag fails with a fixed argument error."""
    result = subprocess.run([".venv/bin/ecs-ec", "identity", "bootstrap-admin", "--email", "admin@example.test",
                             "--password", "Synthetic-never-reflect-this"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "Synthetic-never-reflect-this" not in result.stdout + result.stderr
