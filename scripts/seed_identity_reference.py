"""Explicit synthetic fixture seed for an EMPTY separate *_test DB, never operational bootstrap.

Run with `uv run python scripts/seed_identity_reference.py --password-file /protected/file`.
The protected file contains only the initial synthetic password and requires mode 0600.
Production and the application's configured database are rejected before any mutation.
"""

import argparse
import asyncio
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from ecs_ec.core.clock import SystemClock
from ecs_ec.core.database import Database
from ecs_ec.core.settings import Settings
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.audit import IdentityAudit
from ecs_ec.identity.credentials import Credentials
from ecs_ec.identity.models import Account, Guard


async def seed(password_file):
    """Validate exclusive synthetic destination/input, then create four role/state references atomically."""
    settings = Settings()
    raw = os.environ.get("TEST_DATABASE_URL", "")
    target = make_url(raw)
    source = make_url(settings.database_url.get_secret_value())
    if settings.environment == "production" or target.drivername != "postgresql+psycopg" or not (target.database or "").endswith("_test") or target.database == source.database:
        raise ValueError("A separate development/test PostgreSQL database is required")
    path = Path(password_file)
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError("A protected password file with mode 0600 is required")
    password = path.read_text().removesuffix("\n")
    encoded = await Credentials(2).hash(password)
    database = Database(raw)
    clock = SystemClock()
    audit = IdentityAudit(clock, settings.building_timezone)
    try:
        async with UnitOfWork(database.sessions) as uow:
            guard = await uow.session.scalar(select(Guard).where(Guard.id == 1).with_for_update())
            if guard is None or await uow.session.scalar(select(func.count()).select_from(Account)):
                raise ValueError("An empty migrated fixture database is required")
            for role, label in (("administrador_tecnico", "admin"), ("operador", "operator")):
                for status in ("active", "inactive"):
                    now, identifier = clock.now(), uuid4()
                    email = f"{label}-{status}@example.test"
                    row = Account(id=identifier, email=email, email_key=email, role=role, status=status,
                        password_hash=encoded, must_change_password=True, auth_version=1, revision=1,
                        created_at=now, updated_at=now, password_changed_at=now,
                        created_by="process:fixture", updated_by="process:fixture")
                    uow.session.add(row)
                    await audit.changed(uow, account_id=identifier, revision=1, actor_ref="process:fixture",
                        action="identity.account.created", fields=("email", "role", "status", "credential", "renewal"),
                        role=role, status=status, renewal=True, operation_ref=uuid4())
            await uow.commit()
    finally:
        await database.close()


def main():
    """Accept a protected file path only; never a password argument or production destination."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", required=True)
    options = parser.parse_args()
    try:
        asyncio.run(seed(options.password_file))
    except Exception:
        parser.exit(1, "No se crearon las fixtures; revise destino vacío y entrada protegida.\n")
    print("Fixtures sintéticas creadas; requieren renovación inicial.")


if __name__ == "__main__":
    main()
