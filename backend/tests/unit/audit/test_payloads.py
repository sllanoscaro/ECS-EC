"""Payload registration must prevent free-text/secret schemas and reject unregistered results."""

from typing import Literal

import pytest

from ecs_ec.audit.events import PayloadRegistry, SafePayload
from ecs_ec.core.errors import InvalidEvidence


class FreeText(SafePayload):
    """Deliberately unsafe unconstrained text; this schema must not be registered."""

    details: str


class SecretField(SafePayload):
    """Deliberately unsafe field name, even though the value is constrained."""

    smtpBody: Literal["synthetic"]


def test_free_text_schema_rejected():
    """Registration must fail before a generic exception or body could be approved as text."""
    with pytest.raises(ValueError):
        PayloadRegistry().register("synthetic.changed", FreeText)


def test_sensitive_fields_and_results_rejected():
    """Sensitive field names and unapproved outcomes never enter stored evidence."""
    registry = PayloadRegistry()
    registry.register("synthetic.changed", SecretField, results={"succeeded"})
    with pytest.raises(InvalidEvidence):
        registry.validate("synthetic.changed", {"smtpBody": "synthetic"})
    with pytest.raises(InvalidEvidence):
        registry.validate("synthetic.changed", {"smtpBody": "synthetic"}, result="unapproved")
