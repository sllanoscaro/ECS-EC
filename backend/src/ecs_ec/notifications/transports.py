"""Blocking SMTP with explicit DATA acceptance evidence, bounded budget and no automatic downgrade.

Protocol references: https://docs.python.org/3.14/library/smtplib.html . No raw relay
text, exception, credential, address or MIME payload enters a functional reason or log.
"""

import re
import smtplib
import ssl
import time
from dataclasses import dataclass
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY


@dataclass(frozen=True)
class TransportResult:
    """Closed acceptance classification; relay responses are deliberately excluded."""

    outcome: str
    reason: str


class BudgetSMTP(smtplib.SMTP):
    """Adjust each command/reply timeout to the remaining monotonic attempt budget."""

    def __init__(self, *, deadline, socket_timeout):
        """Avoid DNS discovery for HELO and defer all network calls to the bounded stages."""
        self.deadline, self.socket_timeout = deadline, socket_timeout
        super().__init__(local_hostname="ecs-ec.local", timeout=socket_timeout)

    def refresh(self):
        """A late stage cannot receive another full socket timeout after the total budget expires."""
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        self.timeout = min(self.socket_timeout, remaining)
        if self.sock:
            self.sock.settimeout(self.timeout)

    def putcmd(self, cmd, args=""):
        """Apply budget to command writes, including authentication subcommands."""
        self.refresh()
        return super().putcmd(cmd, args)

    def getreply(self):
        """Apply budget before every protocol reply, including TLS and authentication."""
        self.refresh()
        return super().getreply()


class SMTPTransport:
    """One To/envelope recipient; STARTTLS with verified hostname for authenticated production submission."""

    def __init__(self, settings, *, smtp_factory=BudgetSMTP):
        """Inject a private deterministic protocol peer only in tests; no public failure endpoints."""
        self.settings, self.smtp_factory = settings, smtp_factory

    def send(self, recipient, message_id, bodies):
        """Return evidence-based acceptance while always closing the socket; never run on the event loop."""
        options = self.settings
        deadline = time.monotonic() + options.smtp_attempt_timeout
        smtp = None
        transferring = False

        def result(code):
            """Classify an explicit negative SMTP response without storing any relay text."""
            return (
                TransportResult(
                    "no_aceptada_transitoria", "servicio_temporalmente_no_disponible"
                )
                if 400 <= code < 500
                else TransportResult(
                    "no_aceptada_definitiva", "servicio_rechazo_entrega"
                )
            )

        def refresh():
            """Update budget before high-level stages and body transfer."""
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            smtp.timeout = min(options.smtp_socket_timeout, remaining)
            if smtp.sock:
                smtp.sock.settimeout(smtp.timeout)

        try:
            message = EmailMessage(policy=SMTP_POLICY)
            message["From"] = options.mail_from
            message["To"] = recipient
            message["Subject"] = bodies["subject"]
            message["Message-ID"] = message_id
            message.set_content(bodies["text"])
            message.add_alternative(bodies["html"], subtype="html")
            payload = message.as_bytes()
            payload = re.sub(rb"(?m)^\.", b"..", payload)
            if not payload.endswith(b"\r\n"):
                payload += b"\r\n"
            smtp = self.smtp_factory(
                deadline=deadline, socket_timeout=options.smtp_socket_timeout
            )
            refresh()
            code, _ = smtp.connect(options.smtp_host, options.smtp_port)
            if code != 220:
                return result(code)
            refresh()
            code, _ = smtp.ehlo()
            if code != 250:
                return result(code)
            if options.mail_transport == "smtp_produccion":
                refresh()
                smtp.starttls(context=ssl.create_default_context())
                refresh()
                code, _ = smtp.ehlo()
                if code != 250:
                    return result(code)
                refresh()
                smtp.login(
                    options.smtp_username, options.smtp_password.get_secret_value()
                )
            refresh()
            code, _ = smtp.mail(options.mail_from)
            if code != 250:
                return result(code)
            refresh()
            code, _ = smtp.rcpt(recipient)
            if code not in (250, 251):
                return result(code)
            refresh()
            code, _ = smtp.docmd("DATA")
            if code != 354:
                return result(code)
            refresh()
            transferring = True
            smtp.send(payload + b".\r\n")
            refresh()
            code, _ = smtp.getreply()
            if code != 250:
                return result(code)
            try:
                refresh()
                smtp.quit()
            except Exception:
                pass
            return TransportResult("aceptada", "aceptacion_confirmada_por_servicio")
        except ssl.SSLError:
            return (
                TransportResult("indeterminada", "confirmacion_no_disponible")
                if transferring
                else TransportResult(
                    "no_aceptada_definitiva", "configuracion_correo_no_valida"
                )
            )
        except (
            smtplib.SMTPAuthenticationError,
            smtplib.SMTPNotSupportedError,
            ValueError,
        ):
            return TransportResult(
                "no_aceptada_definitiva", "configuracion_correo_no_valida"
            )
        except smtplib.SMTPResponseException as error:
            return result(error.smtp_code)
        except OSError, smtplib.SMTPException:
            return (
                TransportResult("indeterminada", "confirmacion_no_disponible")
                if transferring
                else TransportResult(
                    "no_aceptada_transitoria", "servicio_temporalmente_no_disponible"
                )
            )
        except Exception:
            return TransportResult("indeterminada", "confirmacion_no_disponible")
        finally:
            if smtp:
                try:
                    smtp.close()
                except Exception:
                    pass
