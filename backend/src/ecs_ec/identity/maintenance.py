"""Bounded access-state maintenance; it never deletes accounts, functional audit or protected events."""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import or_, select

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.models import LoginBucket, Preauth, Session


async def validate_rotation(identity):
    """Fail closed if a retired bucket key could still hide a wait or a state younger than thirty minutes."""
    known = {identity.settings.login_bucket_key_id}
    if identity.settings.previous_login_bucket_key_id:
        known.add(identity.settings.previous_login_bucket_key_id)
    now = identity.clock.now()
    async with UnitOfWork(identity.database.sessions) as uow:
        stale = await uow.session.scalar(select(LoginBucket.bucket_key).where(
            LoginBucket.key_id.not_in(known), or_(LoginBucket.blocked_until > now, LoginBucket.updated_at > now-timedelta(minutes=30))).limit(1))
        if stale is not None:
            raise IdentityProblem("identity_unavailable", 503)


async def maintain(identity, batch_size=100):
    """Remove at most batch_size rows per technical table after24h, skipping locks and preserving live buckets."""
    if not 1 <= batch_size <= 1000:
        raise ValueError("Maintenance batch must be between 1 and 1000")
    counts = {"sessions": 0, "preauth": 0, "buckets": 0}
    now = identity.clock.now()
    cutoff = now-timedelta(hours=24)
    async with UnitOfWork(identity.database.sessions) as uow:
        expired = (await uow.session.scalars(select(Session).where(or_(Session.revoked_at <= cutoff,
            Session.idle_expires_at <= cutoff, Session.absolute_expires_at <= cutoff)).order_by(Session.id)
            .limit(batch_size).with_for_update(skip_locked=True))).all()
        for row in expired:
            await uow.session.delete(row)
            counts["sessions"] += 1
        contexts = (await uow.session.scalars(select(Preauth).where(or_(Preauth.expires_at <= cutoff,
            Preauth.consumed_at <= cutoff)).order_by(Preauth.id).limit(batch_size).with_for_update(skip_locked=True))).all()
        for row in contexts:
            await uow.session.delete(row)
            counts["preauth"] += 1
        buckets = (await uow.session.scalars(select(LoginBucket).where(LoginBucket.updated_at <= cutoff)
            .order_by(LoginBucket.bucket_key).limit(batch_size).with_for_update(skip_locked=True))).all()
        for row in buckets:
            current = identity.clock.now()
            if row.blocked_until and current < row.blocked_until:
                continue
            if any(datetime.fromisoformat(value) > current-timedelta(minutes=15) for value in row.failed_at):
                continue
            await uow.session.delete(row)
            counts["buckets"] += 1
        await uow.commit()
    return counts


async def maintenance_loop(identity, app, interval=60):
    """Run inside the monolith lifespan; failure is visible as a fixed flag and cannot grant access."""
    while True:
        try:
            await maintain(identity)
            app.state.identity_maintenance_failed = False
        except Exception:
            # No raw DB/credential exception is emitted before observability007 exists.
            app.state.identity_maintenance_failed = True
        await asyncio.sleep(interval)
