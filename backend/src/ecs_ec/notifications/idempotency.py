"""008 transaction-scoped idempotency; current authorization precedes lookup, replay precedes If-Match."""

import json
from hashlib import sha256

from sqlalchemy import text

from ecs_ec.notifications.models import Idempotency
from ecs_ec.notifications.repository import NotificationProblem


def digest(value):
    """Hash strict canonical functional JSON; never embed raw requests or credentials in a receipt."""
    return sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


async def lookup(session, actor, operation, key, body):
    """Serialize only matching idempotency keys, then return a committed receipt or conflict safely."""
    if (
        not isinstance(key, str)
        or not 1 <= len(key) <= 100
        or any(ord(c) < 33 or ord(c) == 127 for c in key)
    ):
        raise NotificationProblem("idempotency_key_required", 422)
    value = digest([str(actor), operation, key])
    lock = int(value[:16], 16)
    if lock >= 1 << 63:
        lock -= 1 << 64
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
    row = await session.get(Idempotency, (actor, operation, key))
    if row and row.request_hash != digest(body):
        raise NotificationProblem("idempotency_conflict", 409)
    return row


def revision(header, actual):
    """Require an explicit quoted positive revision; equality belongs after lookup of a confirmed replay."""
    if header is None:
        raise NotificationProblem("revision_required", 428)
    if (
        not isinstance(header, str)
        or not header.startswith('"')
        or not header.endswith('"')
        or not header[1:-1].isdigit()
    ):
        raise NotificationProblem("invalid_revision", 422)
    if int(header[1:-1]) != actual:
        raise NotificationProblem("revision_conflict", 412)
