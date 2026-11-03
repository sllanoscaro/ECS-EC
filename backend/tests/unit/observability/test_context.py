"""Exercise trustworthy opaque context and concurrent async task isolation."""

import asyncio
from uuid import uuid4


async def test_concurrent_contexts_and_reset():
    """Sibling tasks retain only their own server context and reset on exit."""
    from ecs_ec.observability.context import current, bind, new_context
    async def operation():
        """Bind one internal context across an await and return its trusted identity."""
        value = new_context()
        with bind(value):
            await asyncio.sleep(0)
            assert current() == value
        return value.operation_ref
    values = await asyncio.gather(*(operation() for _ in range(20)))
    assert len(set(values)) == 20
    assert current().context_status == "unavailable"


def test_recovery_and_explicit_retry():
    """Recovery preserves logical attempt and creates execution; explicit resend changes attempt."""
    from ecs_ec.observability.context import new_context, recover, resend
    first = new_context(publication_ref=uuid4())
    recovered = recover(first)
    assert recovered.operation_ref == first.operation_ref
    assert recovered.attempt_ref == first.attempt_ref
    assert recovered.execution_ref != first.execution_ref
    assert recovered.context_status == "recovered"
    retry = resend(first)
    assert retry.publication_ref == first.publication_ref
    assert retry.attempt_ref != first.attempt_ref


def test_public_headers_do_not_define_context():
    """The new-context API has no public header or arbitrary-string reference seam."""
    import pytest
    from ecs_ec.observability.context import new_context
    with pytest.raises((TypeError, ValueError)):
        new_context(operation_ref="public-request-id")
    with pytest.raises(TypeError):
        new_context(traceparent="00-" + "1" * 32)


def test_semantic_mapping_separates_environments_and_bindings():
    """HMAC mapping is deterministic only for the same trusted namespace/key/version."""
    from ecs_ec.observability.context import opaque_reference
    a = opaque_reference(b"x" * 32, "test", "v1", "binding-a", "same-text")
    assert a == opaque_reference(b"x" * 32, "test", "v1", "binding-a", "same-text")
    assert a != opaque_reference(b"x" * 32, "local", "v1", "binding-a", "same-text")
    assert a != opaque_reference(b"x" * 32, "test", "v1", "binding-b", "same-text")
