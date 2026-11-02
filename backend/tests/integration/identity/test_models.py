"""PostgreSQL constraints and migration ownership for all five identity tables."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from ecs_ec.identity.models import Account, Session, Preauth, LoginBucket, Guard
from ecs_ec.core.unit_of_work import UnitOfWork


async def test_schema_ownership(identity_db):
    """Migrate only installed owners; guard is singleton and protected FKs use RESTRICT."""
    async with identity_db.engine.connect() as connection:
        names = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        assert {"identity_account", "identity_session", "identity_preauth", "identity_login_bucket", "identity_guard"} <= set(names)
        assert not any(name.startswith("notification") for name in names)
        assert await connection.scalar(text("SELECT count(*) FROM identity_guard WHERE id=1")) == 1
        fks = await connection.run_sync(lambda conn: inspect(conn).get_foreign_keys("identity_session"))
        assert fks[0]["options"]["ondelete"] == "RESTRICT"


async def test_canonical_unique_including_inactive(identity_db, account_factory):
    """Inactive accounts retain their canonical identity and cannot be duplicated."""
    original = await account_factory(status="inactive")
    async with UnitOfWork(identity_db.sessions) as uow:
        values = {column.name: getattr(original, column.name) for column in Account.__table__.columns}
        from uuid import uuid4
        values["id"] = uuid4()
        uow.session.add(Account(**values))
        with pytest.raises(IntegrityError):
            await uow.session.flush()


@pytest.mark.parametrize(("column", "value"), [("role", "programador"), ("status", "deleted"), ("auth_version", 0), ("revision", -1)])
async def test_account_constraints(identity_db, account_factory, column, value):
    """The database rejects unknown roles/states and nonpositive versions, independent of HTTP."""
    row = await account_factory()
    async with UnitOfWork(identity_db.sessions) as uow:
        with pytest.raises(IntegrityError):
            await uow.session.execute(text(f"UPDATE identity_account SET {column}=:value WHERE id=:id"), {"value": value, "id": row.id})


async def test_digest_uniqueness_and_restrict(identity_db, account_factory, session_factory):
    """A session stores32-byte digest/UTC, rejects duplicate digest and protects its permanent account FK."""
    from uuid import uuid4
    account = await account_factory()
    _, principal = await session_factory(account)
    async with UnitOfWork(identity_db.sessions) as uow:
        row = await uow.session.get(Session, principal.session_id)
        assert len(row.token_digest) == 32 and row.created_at.utcoffset().total_seconds() == 0
        values = {column.name: getattr(row, column.name) for column in Session.__table__.columns}
        values["id"] = uuid4()
        uow.session.add(Session(**values))
        with pytest.raises(IntegrityError):
            await uow.session.flush()
    async with UnitOfWork(identity_db.sessions) as uow:
        with pytest.raises(IntegrityError):
            await uow.session.execute(text("DELETE FROM identity_account WHERE id=:id"), {"id": account.id})


@pytest.mark.parametrize("statement", [
    "INSERT INTO identity_guard (id) VALUES (2)",
    "INSERT INTO identity_guard (id) VALUES (1)",
    "INSERT INTO identity_login_bucket (bucket_key,failed_at,updated_at,key_id) VALUES (decode('00','hex'),'[]',now(),'test')",
    "INSERT INTO identity_login_bucket (bucket_key,failed_at,updated_at,key_id) VALUES (decode(repeat('00',32),'hex'),'[1,2,3,4,5,6]',now(),'test')",
    "INSERT INTO identity_preauth (id,token_digest,created_at,expires_at,csrf_key_id) VALUES ('00000000-0000-0000-0000-000000000099',decode(repeat('00',32),'hex'),now(),now()+interval '11 minutes','test')",
])
async def test_guard_bucket_and_preauth_constraints(identity_db, statement):
    """Real DB constraints prevent a second guard, bad digest/list cardinality and extended preauth lifetime."""
    async with UnitOfWork(identity_db.sessions) as uow:
        with pytest.raises(IntegrityError):
            await uow.session.execute(text(statement))
