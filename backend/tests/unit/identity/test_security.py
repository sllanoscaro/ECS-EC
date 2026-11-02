"""Transport and CSRF trust boundaries reject forged proxies, missing origins and cross-context tokens."""

import pytest
from starlette.requests import Request

from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.security import csrf, new_secret, request_context, verify_csrf, verify_origin
from ecs_ec.identity.settings import IdentitySettings


def configuration(**changes):
    """Use synthetic persistent keys and a public HTTPS origin; HTTP is deliberately not enabled."""
    return IdentitySettings(_env_file=None, csrf_key="a"*43, login_bucket_key="b"*43,
                            public_url="https://platform.example.test", environment="test", **changes)


def request(*, peer="203.0.113.1", scheme="http", headers=None):
    """Construct an ASGI transport context only, without a fake business endpoint or credentials."""
    values = {"host": "platform.example.test"} | (headers or {})
    return Request({"type": "http", "method": "POST", "path": "/api/v1/auth/login", "scheme": scheme,
        "query_string": b"", "server": ("platform.example.test", 443), "client": (peer, 12345),
        "headers": [(key.encode(), value.encode()) for key, value in values.items()]})


def test_untrusted_forwarded_proto_never_enables_http_credentials():
    """A public caller cannot claim HTTPS by supplying X-Forwarded-Proto."""
    with pytest.raises(IdentityProblem) as failure:
        request_context(request(headers={"x-forwarded-proto": "https"}), configuration())
    assert failure.value.code == "https_required"


def test_explicit_proxy_and_origin_ip_chain():
    """Only configured proxy peers can supply protocol and the trusted suffix of an IP chain."""
    settings = configuration(trusted_proxies=["10.0.0.0/24"])
    value = request(peer="10.0.0.8", headers={"x-forwarded-proto": "https", "x-forwarded-for": "198.51.100.4, 10.0.0.9"})
    assert request_context(value, settings) == "198.51.100.4"
    with pytest.raises(IdentityProblem):
        request_context(request(peer="10.0.0.8", headers={"x-forwarded-proto": "https,http"}), settings)


@pytest.mark.parametrize("headers", [{}, {"origin": "https://elsewhere.example.test"}, {"origin": "null"}, {"referer": "https://[malformed"}])
def test_mutating_origin_is_required_and_exact(headers):
    """Missing, foreign, opaque or malformed origins cannot reach credential processing."""
    with pytest.raises(IdentityProblem):
        verify_origin(request(scheme="https", headers=headers), configuration())


def test_referer_fallback_and_namespaced_csrf():
    """Valid Referer is a fallback only; presession tokens never authorize a human-session mutation."""
    settings = configuration()
    verify_origin(request(scheme="https", headers={"referer": settings.origin+"/cuenta/"}), settings)
    bearer = new_secret()
    preauth = csrf(settings, "preauth", bearer)
    assert preauth != csrf(settings, "session", bearer)
    with pytest.raises(IdentityProblem):
        verify_csrf(settings, "session", bearer, preauth)


def test_public_peer_cannot_spoof_loopback_development_host():
    """Even explicit local development cannot process HTTP credentials received from a public peer."""
    settings = IdentitySettings(_env_file=None, csrf_key="a"*43, login_bucket_key="b"*43,
        public_url="http://localhost:8000", environment="test", development_http=True)
    with pytest.raises(IdentityProblem) as failure:
        request_context(request(peer="8.8.8.8", headers={"host": "localhost:8000"}), settings)
    assert failure.value.code == "https_required"
