"""008 current006 account eligibility under caller-owned ordered locks; no free email recipients."""

from uuid import UUID

from ecs_ec.identity.services import recipient_eligible
from ecs_ec.notifications.catalog import required_permissions
from ecs_ec.notifications.idempotency import digest
from ecs_ec.notifications.repository import NotificationProblem, lock_accounts


async def eligible_accounts(session, config, *, extra=()):
    """Lock accounts by UUID and require each configured recipient to hold all content grants."""
    ids = [UUID(raw) for raw in config["recipient_ids"]]
    accounts = await lock_accounts(session, set(ids) | set(extra))
    required = required_permissions(config)
    if any(
        not recipient_eligible(accounts.get(identifier), required) for identifier in ids
    ):
        raise NotificationProblem("recipient_ineligible", 422)
    return accounts


def fingerprint(config, accounts):
    """Bind previews to account/auth revisions and current grants without storing email or identity credentials."""
    return digest(
        [
            (
                identifier,
                accounts[UUID(identifier)].revision,
                accounts[UUID(identifier)].auth_version,
                accounts[UUID(identifier)].role,
                accounts[UUID(identifier)].status,
                accounts[UUID(identifier)].must_change_password,
            )
            for identifier in sorted(config["recipient_ids"])
        ]
    )
