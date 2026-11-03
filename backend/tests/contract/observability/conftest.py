"""Reuse explicit test-only gateway fixtures for HTTP boundary contracts; never auto-start production."""

from backend.tests.integration.observability.conftest import gateway_root, gateway_provision, gateway_client  # noqa: F401
