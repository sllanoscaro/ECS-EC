"""Check privacy before serialization/queues; no malicious object is stringified."""

import pytest


class Hostile:
    """Input which exposes a marker if arbitrary object coercion occurs."""

    def __str__(self):
        """Fail the test if a sanitizer tries to stringify a business object."""
        raise AssertionError("Never stringify private objects")


@pytest.mark.parametrize("field", ["password", "session", "email", "ip", "body", "exception", "extra", "url", "sql", "energy", "amount"])
def test_free_fields_rejected_before_queue(safe_event, field):
    """Sensitive or free-form fields reject the whole event before any sink sees it."""
    from ecs_ec.observability.events import RejectedEvent, serialize
    safe_event[field] = Hostile()
    with pytest.raises(RejectedEvent):
        serialize(safe_event)


def test_arbitrary_objects_in_allowed_fields_rejected(safe_event):
    """Allowed field names never grant permission to stringify arbitrary payloads."""
    from ecs_ec.observability.events import RejectedEvent, serialize
    safe_event["code"] = Hostile()
    with pytest.raises(RejectedEvent):
        serialize(safe_event)
