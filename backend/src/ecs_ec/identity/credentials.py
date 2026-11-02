"""Exact Unicode credentials and bounded off-loop Argon2id; no network email checks."""

import asyncio
import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from email_validator import validate_email, EmailNotValidError

from ecs_ec.identity.errors import IdentityProblem


def normalize_email(value: str, local: bool) -> tuple[str, str]:
    """Validate <=320 Unicode points, trim outside spaces, and return presentation/canonical IDNA key."""
    if not isinstance(value, str) or len(value) > 320:
        raise IdentityProblem("email_invalid", 422)
    try:
        normalized = validate_email(value.strip(), check_deliverability=False, test_environment=local)
        key = normalized.local_part.casefold() + "@" + normalized.ascii_domain.lower()
        return normalized.normalized, key
    except (EmailNotValidError, UnicodeError):
        raise IdentityProblem("email_invalid", 422) from None


def valid_password(value: str) -> str:
    """Require 15..128 Unicode code points and exact encodable UTF-8; never transform the input."""
    if not isinstance(value, str) or not 15 <= len(value) <= 128:
        raise IdentityProblem("invalid_input", 422)
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise IdentityProblem("invalid_input", 422) from None
    return value


class Credentials:
    """Bound CPU/memory concurrency, including cancelled callers whose threads are still running."""

    def __init__(self, concurrency):
        """Use the approved Argon2id parameters; no hash operation runs on the event loop."""
        self.hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, salt_len=16, hash_len=32, type=Type.ID)
        self.limit = asyncio.Semaphore(concurrency)
        self.dummy = None
        self._prepare_lock = asyncio.Lock()

    async def _run(self, function, *args):
        """Hold the concurrency slot until the worker ends, even after request cancellation."""
        async with self.limit:
            task = asyncio.create_task(asyncio.to_thread(function, *args))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise

    async def prepare(self):
        """Prepare one non-account dummy PHC before traffic, using the same memory/cost profile."""
        async with self._prepare_lock:
            if self.dummy is None:
                self.dummy = await self._run(self.hasher.hash, secrets.token_urlsafe(32))

    async def hash(self, value):
        """Validate a complete password and return a salted irreversible PHC string."""
        return await self._run(self.hasher.hash, valid_password(value))

    async def verify(self, value, encoded):
        """Verify exact bytes off-loop; unknown accounts pay dummy cost and always fail."""
        try:
            valid_password(value)
        except IdentityProblem:
            return False
        if encoded is None:
            await self.prepare()
        try:
            matched = await self._run(self.hasher.verify, encoded or self.dummy, value)
            return bool(matched and encoded is not None)
        except (VerificationError, InvalidHashError):
            return False
