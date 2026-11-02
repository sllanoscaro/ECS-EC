"""Explicit account/session projections; callers own transaction and authorization boundaries."""

from sqlalchemy import select

from ecs_ec.identity.models import Account
from ecs_ec.identity.schemas import AccountView


def account_view(row: Account) -> AccountView:
    """Project only the eight fields approved by the administrative HTTP contract."""
    return AccountView.model_validate(row)


async def account_by_key(session, email_key):
    """Read current account snapshot by canonical key without retaining a consumer lock."""
    return await session.scalar(select(Account).where(Account.email_key == email_key))
