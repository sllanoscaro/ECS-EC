"""Known normalization and Unicode password boundaries, using the real Argon2 implementation."""

import pytest

from ecs_ec.identity.credentials import normalize_email, valid_password, Credentials
from ecs_ec.identity.errors import IdentityProblem


def test_email_equivalence_and_distinctions():
    """Canonicalization folds case/IDNA and outside spaces, without merging dots or plus suffixes."""
    assert normalize_email("  PERSON@Example.test ", True)[1] == "person@example.test"
    assert normalize_email("Person@bücher.de", True)[1] == "person@xn--bcher-kva.de"
    assert normalize_email("a.b+tag@example.test", True)[1] == "a.b+tag@example.test"
    with pytest.raises(IdentityProblem):
        normalize_email("person@example.test", False)


@pytest.mark.parametrize("length", [15, 128])
async def test_password_unicode_exact(length):
    """Unicode code points and leading/trailing spaces are hashed without normalization/truncation."""
    value = " " + "é" * (length - 2) + " "
    valid_password(value)
    credentials = Credentials(2)
    encoded = await credentials.hash(value)
    assert encoded.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert await credentials.verify(value, encoded)
    assert not await credentials.verify(value.strip(), encoded)


@pytest.mark.parametrize("length", [14, 129])
def test_password_invalid_length(length):
    """Reject complete out-of-range values; there is no silent truncation."""
    with pytest.raises(IdentityProblem):
        valid_password("x" * length)
