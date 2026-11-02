"""Safe identity Problems; neither public messages nor field errors accept raw exception input."""

from uuid import uuid4

from ecs_ec.core.errors import PlatformError

DETAILS = {
    "invalid_credentials": "No fue posible ingresar con esas credenciales",
    "login_wait": "Debe esperar antes de volver a intentar ingresar.",
    "session_required": "Debe iniciar sesión de nuevo.",
    "forbidden": "No tiene permiso para realizar esta acción.",
    "password_change_required": "Debe renovar su contraseña antes de continuar.",
    "csrf_invalid": "La comprobación de seguridad venció. Recargue e intente de nuevo.",
    "origin_invalid": "El origen de la solicitud no está permitido.",
    "https_required": "Se requiere una conexión protegida.",
    "invalid_input": "Revise los campos indicados.",
    "email_invalid": "El correo no es admisible.",
    "email_conflict": "El correo ya está registrado.",
    "last_active_administrator": "Debe conservar al menos un Administrador técnico activo.",
    "not_found": "No se encontró el recurso.",
    "revision_required": "Recargue la cuenta antes de modificarla.",
    "revision_conflict": "La cuenta cambió. Recargue antes de continuar.",
    "identity_coordination_retry": "La operación requiere un nuevo intento.",
    "current_password_invalid": "La contraseña actual no es válida.",
    "password_unchanged": "La nueva contraseña debe ser distinta de la actual.",
    "use_own_password_change": "Use el cambio de contraseña personal.",
    "bootstrap_not_empty": "La instalación ya contiene cuentas.",
    "recovery_not_allowed": "La recuperación requiere una cuenta administrativa activa.",
    "identity_unavailable": "No se pudo confirmar la operación. Recargue antes de repetirla.",
}


class IdentityProblem(PlatformError):
    """Represent a typed safe failure with correlation and no user-supplied detail text."""

    def __init__(self, code, status=403, *, operation_ref=None, retry_after=None, field_errors=None, audited=False):
        """Select a fixed public message, status and sanitized metadata; reject unknown codes."""
        self.code = code
        self.detail = DETAILS[code]
        self.status = status
        self.operation_ref = operation_ref or uuid4()
        self.retry_after = retry_after
        self.field_errors = field_errors or []
        self.audited = audited
        Exception.__init__(self, self.detail)

    def body(self):
        """Return the public Problem contract without exception context or received values."""
        return {"code": self.code, "detail": self.detail, "operation_ref": str(self.operation_ref),
                "field_errors": self.field_errors}
