"""SMTP protocol boundaries distinguish explicit rejection, lost DATA confirmation and accepted QUIT failure."""

import ssl
from types import SimpleNamespace

import pytest
from ecs_ec.notifications.settings import NotificationSettings
from ecs_ec.notifications.transports import SMTPTransport


class Relay:
    """Internal deterministic SMTP peer double; never exposed as an HTTP failure control."""

    def __init__(self, *, final=(250, b"ok"), data=(354, b"go"), quit_fails=False):
        """Specify only protocol outcomes without credentials or personal message logging."""
        self.final, self.data_reply, self.quit_fails = final, data, quit_fails
        self.socket = SimpleNamespace(settimeout=lambda _: None)
        self.sock = self.socket
        self.receivers = []
        self.closed = False

    def connect(self, *args):
        """Return an explicit synthetic220 greeting."""
        return 220, b"ready"

    def ehlo(self):
        """Accept the greeting without advertising an external service."""
        return 250, b"hello"

    def mail(self, address):
        """Confirm the synthetic authorized sender."""
        return 250, b"ok"

    def rcpt(self, address):
        """Retain the sole envelope address for an assertion within this private test."""
        self.receivers.append(address)
        return 250, b"ok"

    def docmd(self, command):
        """Return the configured DATA pre-transfer reply."""
        assert command == "DATA"
        return self.data_reply

    def send(self, data):
        """Hold synthetic MIME bytes only in this test instance."""
        self.body = data

    def getreply(self):
        """Return or lose the configured final DATA acknowledgement."""
        if isinstance(self.final, Exception):
            raise self.final
        return self.final

    def quit(self):
        """Simulate clean shutdown or loss after DATA acceptance."""
        if self.quit_fails:
            raise OSError("synthetic disconnection")

    def close(self):
        """Expose deterministic resource closure for assertions."""
        self.closed = True


@pytest.mark.parametrize(
    ("final", "expected"),
    [
        ((250, b"ok"), "aceptada"),
        ((451, b"later"), "no_aceptada_transitoria"),
        ((550, b"rejected"), "no_aceptada_definitiva"),
        (TimeoutError(), "indeterminada"),
        (ssl.SSLError(), "indeterminada"),
    ],
)
def test_final_data_reply_controls_outcome(final, expected):
    """Only an actual positive final DATA response confirms acceptance."""
    relay = Relay(final=final)
    result = SMTPTransport(
        NotificationSettings(_env_file=None), smtp_factory=lambda **_: relay
    ).send(
        "person@example.test",
        "<one@example.test>",
        dict(subject="Resumen", text="Prueba", html="<p>Prueba</p>"),
    )
    assert result.outcome == expected and relay.closed
    assert relay.receivers == ["person@example.test"]
    assert b"Cc:" not in relay.body and b"Bcc:" not in relay.body


def test_quit_failure_preserves_confirmed_acceptance():
    """QUIT is cleanup; its failure never changes a positive DATA outcome into a retry."""
    relay = Relay(quit_fails=True)
    result = SMTPTransport(
        NotificationSettings(_env_file=None), smtp_factory=lambda **_: relay
    ).send(
        "person@example.test",
        "<one@example.test>",
        dict(subject="Resumen", text="Prueba", html="<p>Prueba</p>"),
    )
    assert result.outcome == "aceptada"


def test_data_command_rejection_is_confirmed_nonacceptance():
    """A450 before transfer can retry safely and never transmits the message body."""
    relay = Relay(data=(450, b"busy"))
    result = SMTPTransport(
        NotificationSettings(_env_file=None), smtp_factory=lambda **_: relay
    ).send(
        "person@example.test",
        "<one@example.test>",
        dict(subject="Resumen", text="Prueba", html="<p>Prueba</p>"),
    )
    assert result.outcome == "no_aceptada_transitoria" and not hasattr(relay, "body")


def test_production_tls_verifies_certificate_and_hostname_before_authentication():
    """Authenticated submission receives a default verified SSLContext; no plaintext fallback is attempted."""

    class ProductionRelay(Relay):
        """Private protocol observer checks the TLS/auth ordering without contacting any relay."""

        def starttls(self, *, context):
            """Assert standard certificate verification and hostname checks are enabled."""
            assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
            self.secure = True

        def login(self, username, password):
            """Credentials are supplied only after a successful TLS boundary."""
            assert (
                self.secure
                and username == "synthetic"
                and password == "synthetic-test-only"
            )

    options = NotificationSettings(
        _env_file=None,
        notification_enabled=True,
        mail_transport="smtp_produccion",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_starttls=True,
        smtp_username="synthetic",
        smtp_password="synthetic-test-only",
        mail_from="ecs@example.com",
        app_public_base_url="https://example.com",
    )
    relay = ProductionRelay()
    result = SMTPTransport(options, smtp_factory=lambda **_: relay).send(
        "recipient@example.com",
        "<one@example.com>",
        dict(subject="Resumen", text="Prueba", html="<p>Prueba</p>"),
    )
    assert result.outcome == "aceptada"
