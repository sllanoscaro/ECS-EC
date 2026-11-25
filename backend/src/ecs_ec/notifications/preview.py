"""008 preview tokens are opaque, hashed and permission/config/tzdata bound; preview never sends or activates."""

from datetime import timedelta
from hashlib import sha256
from secrets import token_urlsafe

from ecs_ec.notifications.calendar import next_occurrences, stamp, tzdata_version
from ecs_ec.notifications.idempotency import digest
from ecs_ec.notifications.models import Preview
from ecs_ec.notifications.recipients import fingerprint
from ecs_ec.notifications.repository import NotificationProblem


async def create(session, actor, config, accounts, now):
    """Persist an expiring token digest and return three real future slots or no urgent prediction."""
    dates = (
        next_occurrences(config["schedule"], config["timezone"], now)
        if config["mode"] == "periodica"
        else []
    )
    from ecs_ec.notifications.schemas import instant

    expires = (
        min(now + timedelta(minutes=5), instant(dates[0]["resolved_at"]))
        if dates
        else now + timedelta(minutes=5)
    )
    token = token_urlsafe(32)
    session.add(
        Preview(
            token_hash=sha256(token.encode()).hexdigest(),
            actor_id=actor,
            config_hash=digest(config),
            permissions_hash=fingerprint(config, accounts),
            tzdata_version=tzdata_version(),
            expires_at=expires,
            created_at=now,
        )
    )
    return dict(
        valid=True,
        next_occurrences=dates,
        tzdata_version=tzdata_version(),
        preview_token=token,
        expires_at=stamp(expires),
        warnings=["Ventana inicial vacía: aún no hay período observado."]
        if any(d["initial_window_empty"] for d in dates)
        else [],
    )


async def require(session, token, actor, config, accounts, now):
    """Reject expired or changed context using current locked accounts; tokens grant no authorization themselves."""
    row = (
        await session.get(Preview, sha256(token.encode()).hexdigest())
        if isinstance(token, str) and 1 <= len(token) <= 200
        else None
    )
    if (
        row is None
        or row.actor_id != actor
        or row.expires_at <= now
        or row.config_hash != digest(config)
        or row.permissions_hash != fingerprint(config, accounts)
        or row.tzdata_version != tzdata_version()
    ):
        raise NotificationProblem("preview_stale", 409)
