"""Escaped text/HTML from the same closed snapshot as protected notification history."""

from html import escape
from urllib.parse import urlsplit

from ecs_ec.notifications.schemas import validate

STATUS = {
    "sin_novedades": "Sin novedades",
    "disponible": "Información disponible",
    "informacion_insuficiente": "Información insuficiente",
}
COVERAGE = {
    "completa": "Completa",
    "incompleta": "Incompleta",
    "desconocida": "Desconocida",
}


def render(content, settings, delivery_id=None):
    """Render one recipient-independent body; envelope addressing is exclusively the transport's responsibility."""
    validate("FunctionalContent", content)
    lines = [
        content["building_name"],
        content["headline"],
        f"Regla {content['rule_id']} · versión {content['rule_version']}",
        STATUS[content["data_status"]],
        f"Zona: {content['timezone']}",
        f"Corte: {content['cutoff_at']}",
    ]
    if content["window"]:
        lines.append(
            f"Período: [{content['window']['start']}, {content['window']['end']})"
        )
    if content.get("initial_window_empty"):
        lines.append("Ventana inicial vacía: sin período observado.")
    if content["is_late"]:
        lines.append("Preparado después del horario o período indicado.")
    condition = content.get("condition")
    if condition:
        if condition["kind"] == "consumo":
            comparison = {
                "gt": "mayor que",
                "gte": "mayor o igual que",
                "lt": "menor que",
                "lte": "menor o igual que",
            }[condition["comparison"]]
            lines.append(
                f"Condición: {condition['category_id']} {comparison} {condition['threshold_kwh']} kWh; ventana {condition['window']['kind']}."
            )
        elif condition["kind"] == "ausencia_datos":
            lines.append(
                f"Condición: {condition['category_id']}, sin datos nuevos durante {condition['silence_minutes']} minutos."
            )
        else:
            lines.append(
                "Suceso funcional: "
                + {
                    "recepcion_rechazada": "Recepción con rechazos",
                    "calculo_fallido": "Fallo de cálculo",
                    "pdf_fallido": "Fallo de generación PDF",
                }[condition["event_type"]]
            )
    if content.get("episode_id"):
        lines.append("Episodio: " + content["episode_id"])
    if content.get("detected_at"):
        lines.append("Detección: " + content["detected_at"])
    if content.get("source_event_at"):
        lines.append("Fecha del suceso: " + content["source_event_at"])
    if content.get("source_event"):
        ref = content["source_event"]
        lines.append(
            f"Origen funcional: {ref['module']} · {ref['entity_id']} · revisión {ref['revision']}"
        )
    for item in content["summary_items"]:
        label = "Eventos" if item["coverage"] == "completa" else "Eventos observados"
        lines.append(
            f"{item['kind']}: {label}: {item['count'] if item['count'] is not None else 'No disponible'} · Cobertura: {COVERAGE[item['coverage']]}"
        )
        for period in item["covered_periods"]:
            lines.append(f"Historia cubierta: [{period['start']}, {period['end']})")
        for period in item["known_gaps"]:
            lines.append(f"Hueco conocido: [{period['start']}, {period['end']})")
        if item["limitation_code"]:
            lines.append("Limitación: " + item["limitation_code"])
    for evidence in content["evidence"]:
        lines.append(
            f"{evidence['category_id']}: {evidence['value_kwh'] if evidence['value_kwh'] is not None else 'No disponible'} kWh · {evidence['quality']} · {evidence['origin']}"
        )
        lines.append(
            "Base: " + (", ".join(evidence["basis_categories"]) or "No aplica")
        )
        lines.append(
            f"Período: [{evidence['window']['start']}, {evidence['window']['end']})"
        )
        lines.append(evidence["scope_description"])
    for period in content["recovered_periods"]:
        lines.append(f"Período recuperado: [{period['start']}, {period['end']})")
    if settings.mail_transport == "local_prueba":
        lines.append(
            "Correo local de prueba: aceptado por el capturador, sin entrega externa."
        )
    lines.append(
        "La aceptación por el servicio de correo no acredita recepción ni lectura."
    )
    paths = list(content["protected_paths"])
    if delivery_id:
        paths.insert(0, "/notificaciones?entrega=" + str(delivery_id))
    links = []
    for path in dict.fromkeys(paths):
        parsed = urlsplit(path)
        if (
            not path.startswith("/")
            or path.startswith("//")
            or "\\" in path
            or parsed.netloc
            or any(ord(c) < 32 for c in path)
        ):
            raise ValueError("Protected local path required")
        links.append(settings.app_public_base_url.rstrip("/") + path)
    text = "\n".join(lines + ["Consultar con sesión y permisos vigentes:"] + links)
    html = (
        '<!doctype html><html lang="es"><body>'
        + "".join("<p>" + escape(line) + "</p>" for line in lines)
        + "<p>Consultar con sesión y permisos vigentes:</p>"
        + "".join(
            '<p><a href="'
            + escape(url, quote=True)
            + '">Abrir detalle protegido</a></p>'
            for url in links
        )
        + "</body></html>"
    )
    subject = "".join(c for c in content["headline"] if ord(c) >= 32 and ord(c) != 127)[
        :120
    ]
    return dict(subject=subject, text=text, html=html)
