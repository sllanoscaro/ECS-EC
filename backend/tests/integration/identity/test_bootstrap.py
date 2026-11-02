"""Bootstrap uses the real guard and account evidence without notification tables."""

import asyncio

from sqlalchemy import func, select

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.models import Account


async def test_two_bootstraps_create_once(identity, identity_db):
    """Independent concurrent service calls serialize at PostgreSQL's singleton guard."""
    results = await asyncio.gather(
        identity.bootstrap("first@example.test", "Synthetic first password"),
        identity.bootstrap("second@example.test", "Synthetic second password"), return_exceptions=True)
    assert sum(isinstance(row, Account) for row in results) == 1
    assert sum(isinstance(row, IdentityProblem) and row.code == "bootstrap_not_empty" for row in results) == 1
    async with UnitOfWork(identity_db.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(Account)) == 1
        row = await uow.session.scalar(select(Account))
        assert row.role == "administrador_tecnico" and row.must_change_password
