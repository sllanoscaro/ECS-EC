"""008 fixed functional content→current006 grant mapping; no technical signals are email content."""

PERMISSIONS = {
    "recepcion": "consumption.read",
    "calidad": "consumption.read",
    "cambios_administrativos": "administration.history.read",
    "consumo": "consumption.read",
    "ausencia_datos": "consumption.read",
    "recepcion_rechazada": "consumption.read",
    "calculo_fallido": "costs.read",
    "pdf_fallido": "reports.read",
}


def content_types(config):
    """Urgent content is derived from the validated condition; periodic content is an explicit nonempty set."""
    if config["mode"] == "periodica":
        return tuple(config["content_types"])
    condition = config["condition"]
    return (
        condition["event_type"]
        if condition["kind"] == "evento_sistema"
        else condition["kind"],
    )


def required_permissions(config):
    """Return every required current grant; content is never silently trimmed for an ineligible recipient."""
    return tuple(sorted({PERMISSIONS[kind] for kind in content_types(config)}))


def catalog():
    """Return only approved vocabulary/permissions, not accounts, secrets or private diagnostics."""
    return dict(
        periodic_content_types=["recepcion", "calidad", "cambios_administrativos"],
        urgent_event_types=["recepcion_rechazada", "calculo_fallido", "pdf_fallido"],
        categories=[f"CAT-{i:02}" for i in range(1, 8)],
        required_permissions=[
            dict(content_type=k, permission=v) for k, v in PERMISSIONS.items()
        ],
    )
