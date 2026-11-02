"""Real CLI subprocesses use a protected pseudo-TTY, normal service transactions and no password arguments."""

import errno
import os
import pty
import select
import subprocess
import time

from sqlalchemy import func, select as sql_select

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.models import Account


def run_tty(arguments, password, environment):
    """Answer getpass only after each non-echo prompt; return exit status without exposing the transcript."""
    master, slave = pty.openpty()
    process = subprocess.Popen([".venv/bin/ecs-ec", "identity", *arguments], stdin=slave, stdout=slave, stderr=slave,
                               env=environment, start_new_session=True)
    os.close(slave)
    transcript = b""
    prompts = ["Nueva contraseña: ".encode(), "Confirmar nueva contraseña: ".encode()]
    answered = 0
    deadline = time.monotonic()+20
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    data = os.read(master, 4096)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not data:
                    break
                transcript += data
                if answered < 2 and prompts[answered] in transcript:
                    os.write(master, password.encode()+b"\n")
                    answered += 1
            elif process.poll() is not None:
                break
        if answered != 2:
            raise AssertionError("CLI did not request both protected prompts")
        if password.encode() in transcript:
            raise AssertionError("CLI echoed a synthetic credential")
        return process.wait(timeout=5)
    finally:
        os.close(master)
        if process.poll() is None:
            process.kill()
            process.wait()


async def test_real_bootstrap_and_recovery_tty(identity_db, test_url, identity_settings):
    """Bootstrap creates once; host recovery then resets the same active admin through real CLI/TTY."""
    import asyncio
    environment = {**os.environ, "DATABASE_URL": test_url, "ENVIRONMENT": "test", "PUBLIC_URL": "https://localhost",
        "IDENTITY_ENABLED": "true", "IDENTITY_DEVELOPMENT_HTTP": "false",
        "IDENTITY_CSRF_KEY": identity_settings.csrf_key.get_secret_value(),
        "IDENTITY_LOGIN_BUCKET_KEY": identity_settings.login_bucket_key.get_secret_value()}
    bootstrap = ["bootstrap-admin", "--email", "admin@example.test"]
    second = ["bootstrap-admin", "--email", "second-admin@example.test"]
    codes = await asyncio.gather(*(asyncio.to_thread(run_tty, arguments, "Synthetic CLI initial password", environment) for arguments in (bootstrap, second)))
    assert sorted(codes) == [0, 1]
    async with UnitOfWork(identity_db.sessions) as uow:
        email = await uow.session.scalar(sql_select(Account.email))
    assert await asyncio.to_thread(run_tty, ["bootstrap-admin", "--email", email], "Synthetic CLI initial password", environment) == 1
    assert await asyncio.to_thread(run_tty, ["recover-admin", "--email", email, "--reason", "Ensayo local"],
                                   "Synthetic CLI recovery password", environment) == 0
    async with UnitOfWork(identity_db.sessions) as uow:
        assert await uow.session.scalar(sql_select(func.count()).select_from(Account)) == 1
        row = await uow.session.scalar(sql_select(Account))
        assert row.revision == 2 and row.must_change_password
