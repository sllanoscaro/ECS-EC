"""Stable safe error codes; adapters must not expose raw exception text or SQL."""


class PlatformError(Exception):
    """Represent a public-safe infrastructure failure with a fixed message and code."""

    code = "platform_unavailable"
    message = "La plataforma no está disponible."

    def __init__(self):
        """Construct an error without accepting potentially sensitive dynamic details."""
        super().__init__(self.message)


class SchemaNotReady(PlatformError):
    """Database revision differs from the installed application migration heads."""

    code = "schema_not_ready"
    message = "El esquema de datos requiere migraciones."


class InvalidEvidence(PlatformError):
    """Payload or coverage violates the registered producer contract."""

    code = "invalid_evidence"
    message = "La evidencia no cumple el contrato registrado."
