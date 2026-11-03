"""Durable login/throttle and fresh session admission; all hashing runs before DB locks."""

from ecs_ec.identity.telemetry import observe, stage

import hmac
import math
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.credentials import normalize_email
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.models import Account, LoginBucket, Preauth, Session
from ecs_ec.identity.repository import account_by_key
from ecs_ec.identity.schemas import Principal
from ecs_ec.identity.security import digest, new_secret
from ecs_ec.identity.settings import key_bytes


def bucket_key(key, email, origin):
    """HMAC length-delimited canonical email/IP to avoid ambiguity; neither input is persisted."""
    parts = [value.encode("utf-8", "surrogatepass") for value in (email, origin)]
    return hmac.digest(key_bytes(key), b"".join(len(part).to_bytes(4, "big") + part for part in parts), "sha256")


def wait_problem(until, now):
    """Return the fixed wait Problem with positive seconds rounded upward, never a failure count."""
    return IdentityProblem("login_wait", 429, retry_after=max(1, math.ceil((until-now).total_seconds())))


async def migrate_blocked(identity, key, keys):
    """Migrate a known blocked pair under sorted bucket locks without hashing or extending its deadline."""
    async with UnitOfWork(identity.database.sessions) as uow:
        for candidate in sorted(keys):
            await uow.session.execute(insert(LoginBucket).values(bucket_key=candidate, key_id=keys[candidate],
                failed_at=[], blocked_until=None, updated_at=identity.clock.now()).on_conflict_do_nothing())
        rows = (await uow.session.scalars(select(LoginBucket).where(LoginBucket.bucket_key.in_(keys))
            .order_by(LoginBucket.bucket_key).with_for_update())).all()
        now = identity.clock.now()
        destination = next(row for row in rows if row.bucket_key == key)
        waits = [row.blocked_until for row in rows if row.blocked_until and now < row.blocked_until]
        failures = sorted(value for row in rows for value in row.failed_at if datetime.fromisoformat(value) > now-timedelta(minutes=15))
        destination.failed_at = failures[-5:]
        destination.blocked_until = max(waits) if waits else None
        for row in rows:
            if row.bucket_key != key:
                await uow.session.delete(row)
        problem = wait_problem(destination.blocked_until, now) if waits else None
        await uow.commit()
        stage('commit')
        return problem


@observe('identity.authenticate')
async def login(identity, email, password, preauth_cookie, origin):
    """Authenticate under bucket→preauth→account SHARE→new session, rechecking time/hash/version.

    Unknown/inactive/changed accounts share denial. Failed attempts commit their bucket
    state; invalid CSRF contexts never consume credentials or extend a block.
    """
    try:
        _, canonical = normalize_email(email, identity.settings.environment != "production")
        valid_email = True
    except IdentityProblem:
        canonical, valid_email = email.strip().casefold(), False
    key = bucket_key(identity.settings.login_bucket_key, canonical, origin)
    keys = {key: identity.settings.login_bucket_key_id}
    if identity.settings.previous_login_bucket_key:
        keys[bucket_key(identity.settings.previous_login_bucket_key, canonical, origin)] = identity.settings.previous_login_bucket_key_id
    async with UnitOfWork(identity.database.sessions) as uow:
        buckets = (await uow.session.scalars(select(LoginBucket).where(LoginBucket.bucket_key.in_(keys)))).all()
        now = identity.clock.now()
        for row in buckets:
            if row.blocked_until and now < row.blocked_until:
                if len(keys) > 1:
                    problem = await migrate_blocked(identity, key, keys)
                    if problem:
                        raise problem
                else:
                    raise wait_problem(row.blocked_until, now)
        snapshot = await account_by_key(uow.session, canonical) if valid_email else None
        if snapshot:
            # Keep a detached hash/version capture; UoW rollback expires attached ORM rows.
            uow.session.expunge(snapshot)
    stage('validate')
    matched = await identity.credentials.verify(password, snapshot.password_hash if snapshot else None)
    async with UnitOfWork(identity.database.sessions) as uow:
        for candidate in sorted(keys):
            await uow.session.execute(insert(LoginBucket).values(bucket_key=candidate, key_id=keys[candidate],
                failed_at=[], blocked_until=None, updated_at=identity.clock.now()).on_conflict_do_nothing())
        buckets = (await uow.session.scalars(select(LoginBucket).where(LoginBucket.bucket_key.in_(keys)).order_by(
            LoginBucket.bucket_key).with_for_update())).all()
        bucket = next(row for row in buckets if row.bucket_key == key)
        context = await uow.session.scalar(select(Preauth).where(Preauth.token_digest == digest(preauth_cookie)).with_for_update())
        account = await uow.session.scalar(select(Account).where(Account.id == snapshot.id).with_for_update(read=True)) if snapshot else None
        now = identity.clock.now()
        for row in buckets:
            if row.blocked_until and now < row.blocked_until:
                raise wait_problem(row.blocked_until, now)
        if context is None or context.consumed_at is not None or now >= context.expires_at or context.csrf_key_id != identity.settings.csrf_key_id:
            raise IdentityProblem("csrf_invalid", 403)
        window_start = now-timedelta(minutes=15)
        # Equal timestamps are separate failed attempts (parallel requests/frozen test clock).
        failures = sorted(stamp for row in buckets for stamp in row.failed_at if datetime.fromisoformat(stamp) > window_start)
        bucket.failed_at = failures[-5:]
        bucket.blocked_until = None
        bucket.updated_at = now
        # Migrate rotation state under the same sorted bucket locks; no active wait is lost.
        for row in buckets:
            if row.bucket_key != key:
                await uow.session.delete(row)
        active_admins = await uow.session.scalar(select(func.count()).select_from(Account).where(
            Account.role == "administrador_tecnico", Account.status == "active"))
        accepted = matched and account is not None and account.status == "active" and active_admins and (
            account.auth_version == snapshot.auth_version and account.password_hash == snapshot.password_hash
            and account.email_key == canonical and account.role in {"operador", "administrador_tecnico"})
        if not accepted:
            bucket.failed_at = (bucket.failed_at + [now.isoformat()])[-5:]
            if len(bucket.failed_at) >= 5:
                bucket.blocked_until = now+timedelta(minutes=15)
            await uow.commit()
            stage('commit')
            problem = wait_problem(bucket.blocked_until, now) if bucket.blocked_until else IdentityProblem("invalid_credentials", 401)
        else:
            bearer = new_secret()
            session = Session(id=uuid4(), token_digest=digest(bearer), account_id=account.id, auth_version=account.auth_version,
                mode="password_change_required" if account.must_change_password else "normal", created_at=now,
                last_activity_at=now, idle_expires_at=now+timedelta(minutes=30), absolute_expires_at=now+timedelta(hours=8),
                revoked_at=None, revocation_code=None, csrf_key_id=identity.settings.csrf_key_id)
            uow.session.add(session)
            context.consumed_at = now
            bucket.failed_at, bucket.blocked_until = [], None
            await uow.commit()
            stage('commit')
            return bearer, Principal.from_rows(account, session, identity.settings.building_id)
    raise problem


@observe('identity.session')
async def resolve(identity, bearer, *, action="session.read", activity="background"):
    """Resolve fresh DB state, authorize, then optionally update activity without reviving an old session."""
    stage('read')
    hashed = digest(bearer)
    if hashed is None:
        raise IdentityProblem("session_required", 401)
    async with UnitOfWork(identity.database.sessions) as uow:
        pair = (await uow.session.execute(select(Account, Session).join(Session, Session.account_id == Account.id).where(
            Session.token_digest == hashed))).one_or_none()
        now = identity.clock.now()
        if not pair or not identity.session_valid(pair[0], pair[1], now):
            raise IdentityProblem("session_required", 401)
        account, session = pair
        principal = Principal.from_rows(account, session, identity.settings.building_id)
        identity.authorize(principal, action, identity.settings.building_id)
    if activity == "interactive" and action != "session.read":
        async with UnitOfWork(identity.database.sessions) as uow:
            # Account first, then session: compatible with guarded mutations and login's SHARE lock.
            account = await uow.session.scalar(select(Account).where(Account.id == principal.account_id).with_for_update(read=True))
            session = await uow.session.scalar(select(Session).where(Session.id == principal.session_id).with_for_update())
            now = identity.clock.now()
            if not identity.session_valid(account, session, now):
                raise IdentityProblem("session_required", 401)
            principal = Principal.from_rows(account, session, identity.settings.building_id)
            identity.authorize(principal, action, identity.settings.building_id)
            session.last_activity_at = max(session.last_activity_at, now)
            session.idle_expires_at = min(session.absolute_expires_at, session.last_activity_at+timedelta(minutes=30))
            principal = Principal.from_rows(account, session, identity.settings.building_id)
            await uow.commit()
            stage('commit')
    return principal


@observe('identity.session')
async def logout(identity, principal):
    """Revoke only the original session under its row lock, leaving other devices untouched."""
    async with UnitOfWork(identity.database.sessions) as uow:
        account = await uow.session.scalar(select(Account).where(Account.id == principal.account_id).with_for_update(read=True))
        session = await uow.session.scalar(select(Session).where(Session.id == principal.session_id).with_for_update())
        if not identity.session_valid(account, session, identity.clock.now()):
            raise IdentityProblem("session_required", 401)
        session.revoked_at, session.revocation_code = identity.clock.now(), "logout"
        await uow.commit()
        stage('commit')
