"""Bounded opaque signed cursors, separated by purpose and tied to exact normalized filters."""

import base64
import hmac
import json

from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.settings import key_bytes


def encode_cursor(settings, kind, filters, position):
    """Serialize safe ordering/cutoff metadata and authenticate it with a persistent namespaced key."""
    data = json.dumps({"kind": kind, "filters": filters, "position": position}, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.digest(key_bytes(settings.csrf_key), b"cursor\0"+data, "sha256")
    return base64.urlsafe_b64encode(signature+data).decode().rstrip("=")


def decode_cursor(settings, raw, kind, filters):
    """Reject tampering, wrong purpose/filters or oversized state without reflecting cursor contents."""
    try:
        if not isinstance(raw, str) or len(raw) > 4096:
            raise ValueError()
        value = base64.b64decode(raw+"="*(-len(raw)%4), altchars=b"-_", validate=True)
        signature, data = value[:32], value[32:]
        expected = hmac.digest(key_bytes(settings.csrf_key), b"cursor\0"+data, "sha256")
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        payload = json.loads(data)
        if payload["kind"] != kind or payload["filters"] != filters:
            raise ValueError()
        return payload["position"]
    except Exception:
        raise IdentityProblem("invalid_input", 422) from None
