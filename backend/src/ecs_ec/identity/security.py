"""Opaque secrets, namespaced CSRF and effective transport/origin from explicitly trusted peers."""

import base64
import hashlib
import hmac
import ipaddress
import re
import secrets
from datetime import timedelta
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import select

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.models import Preauth
from ecs_ec.identity.settings import key_bytes


def new_secret():
    """Return an independent 256-bit base64url bearer; never put it in a database or URL."""
    return secrets.token_urlsafe(32)


def digest(bearer):
    """Hash a bounded correctly shaped opaque cookie; invalid shapes cannot be DB credentials."""
    if not isinstance(bearer, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", bearer):
        return None
    return hashlib.sha256(bearer.encode("ascii")).digest()


def csrf(settings, namespace, bearer):
    """Derive a context-specific CSRF token with a stable external key and distinct namespaces."""
    data = namespace.encode() + b"\0" + bearer.encode("ascii")
    return base64.urlsafe_b64encode(hmac.digest(key_bytes(settings.csrf_key), data, "sha256")).decode().rstrip("=")


def verify_csrf(settings, namespace, bearer, received):
    """Require the cookie-bound token in a header and compare in constant time."""
    if digest(bearer) is None or not isinstance(received, str) or len(received) != 43:
        raise IdentityProblem("csrf_invalid", 403)
    if not hmac.compare_digest(csrf(settings, namespace, bearer), received):
        raise IdentityProblem("csrf_invalid", 403)


def trusted_peer(settings, peer):
    """Trust only configured IP/CIDR peers, never a caller-selected forwarded header."""
    try:
        address = ipaddress.ip_address(peer)
        return any(address in ipaddress.ip_network(network, strict=False) for network in settings.trusted_proxies)
    except ValueError:
        return False


def request_context(request, settings):
    """Validate effective HTTPS/host and return canonical origin IP for the private HMAC bucket.

    Uvicorn must run --no-proxy-headers so the actual peer is available. The loopback
    development origin is used only behind the host's loopback-bound Compose listener.
    """
    peer = request.client.host if request.client else "unknown"
    scheme = request.url.scheme
    if trusted_peer(settings, peer):
        forwarded = request.headers.get("x-forwarded-proto")
        if forwarded in {"https", "http"}:
            scheme = forwarded
    expected = urlsplit(settings.origin)
    if request.headers.get("host", "").lower() != expected.netloc.lower():
        raise IdentityProblem("origin_invalid", 403)
    if scheme != "https" and not (settings.development_http and scheme == "http" and expected.scheme == "http"):
        raise IdentityProblem("https_required", 403)
    if scheme != "https":
        # Docker's loopback-published listener presents a private bridge peer. A real
        # public peer cannot enable this exception by forging Host: localhost.
        try:
            if ipaddress.ip_address(peer).is_global:
                raise IdentityProblem("https_required", 403)
        except ValueError:
            raise IdentityProblem("https_required", 403) from None
    if trusted_peer(settings, peer) and request.headers.get("x-forwarded-for"):
        chain = [value.strip() for value in request.headers["x-forwarded-for"].split(",")] + [peer]
        while len(chain) > 1 and trusted_peer(settings, chain[-1]):
            chain.pop()
        peer = chain[-1]
    try:
        address = ipaddress.ip_address(peer)
        return str(getattr(address, "ipv4_mapped", None) or address)
    except ValueError:
        raise IdentityProblem("origin_invalid", 403) from None


def verify_origin(request, settings, required=True):
    """Require exact Origin or the parsed origin of Referer; reject missing mutation origins."""
    origin = request.headers.get("origin")
    if origin is None and request.headers.get("referer"):
        try:
            parsed = urlsplit(request.headers["referer"])
        except ValueError:
            raise IdentityProblem("origin_invalid", 403) from None
        origin = parsed.scheme + "://" + parsed.netloc
    if (required or origin is not None) and origin != settings.origin:
        raise IdentityProblem("origin_invalid", 403)


async def preauth_context(identity, cookie):
    """Reuse a valid ten-minute context without prolonging it, otherwise create an independent one."""
    now = identity.clock.now()
    async with UnitOfWork(identity.database.sessions) as uow:
        row = await uow.session.scalar(select(Preauth).where(Preauth.token_digest == digest(cookie))) if digest(cookie) else None
        if row is None or row.consumed_at is not None or now >= row.expires_at or row.csrf_key_id != identity.settings.csrf_key_id:
            cookie = new_secret()
            row = Preauth(id=uuid4(), token_digest=digest(cookie), created_at=now, expires_at=now+timedelta(minutes=10),
                          consumed_at=None, csrf_key_id=identity.settings.csrf_key_id)
            uow.session.add(row)
            await uow.commit()
        return cookie, row.expires_at


async def check_preauth(identity, cookie):
    """Read-only early validation; login revalidates the original context under its ordered locks."""
    async with UnitOfWork(identity.database.sessions) as uow:
        row = await uow.session.scalar(select(Preauth).where(Preauth.token_digest == digest(cookie))) if digest(cookie) else None
        if row is None or row.consumed_at is not None or identity.clock.now() >= row.expires_at or row.csrf_key_id != identity.settings.csrf_key_id:
            raise IdentityProblem("csrf_invalid", 403)
