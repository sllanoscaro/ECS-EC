"""Exhaustive fixed action matrix; technical identities and forged roles never authorize."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ecs_ec.identity.permissions import ACTIONS, BASIC, READ, ADMIN, allowed
from ecs_ec.identity.schemas import Principal


def principal(role="operador", mode="normal"):
    """Construct an internal policy-only principal; HTTP never accepts it from a body."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return Principal(uuid4(), uuid4(), 1, role, mode, uuid4(), "synthetic@example.test", 1,
                     now+timedelta(hours=8), now+timedelta(minutes=30))


@pytest.mark.parametrize("role", ["operador", "administrador_tecnico", "programador", "sftp", "", "owner"])
@pytest.mark.parametrize("mode", ["normal", "password_change_required"])
def test_whole_action_matrix(role, mode):
    """Every fixed action is checked by role/mode, independent of HTTP verbs."""
    person = principal(role, mode)
    for action in ACTIONS:
        expected = role in {"operador", "administrador_tecnico"} and (
            action in BASIC or (mode == "normal" and (action in READ or role == "administrador_tecnico")))
        assert allowed(person, action, person.building_id) is expected
    assert not allowed(person, "unknown.action", person.building_id)
    assert not allowed(person, "session.read", uuid4())
    assert not allowed(None, "session.read", person.building_id)


def test_post_pdf_is_read_get_configuration_is_admin():
    """Generation is allowed to an Operator; configuration reading remains administrative."""
    person = principal()
    assert allowed(person, "reports.generate", person.building_id)
    assert not allowed(person, "costs.configuration.read", person.building_id)
