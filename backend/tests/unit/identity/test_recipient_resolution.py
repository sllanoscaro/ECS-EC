"""Recipient eligibility is based on current human state/permissions, without any human session or consumer table."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from ecs_ec.identity.services import recipient_eligible


@pytest.mark.parametrize(("role", "status", "renewal", "expected"), [
    ("operador", "active", False, True), ("administrador_tecnico", "active", False, True),
    ("operador", "inactive", False, False), ("operador", "active", True, False),
    ("programador", "active", False, False), ("sftp", "active", False, False),
])
def test_current_recipient(role, status, renewal, expected):
    """A technical identity or pending renewal cannot become a notification recipient through a human role claim."""
    account = SimpleNamespace(id=uuid4(), role=role, status=status, must_change_password=renewal)
    assert recipient_eligible(account, {"consumption.read"}) is expected
    assert not recipient_eligible(account, {"unknown.permission"})
