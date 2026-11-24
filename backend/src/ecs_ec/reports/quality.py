"""005 functional quality/provenance synthesis, grouped by shared cause instead of suppressing limitations."""

from collections import defaultdict
from ecs_ec.reports.energy_table import MODES

REASONS = {
    "partial_calculation_basis": "Total calculado solo con las categorías disponibles",
    "missing_coverage": "Cobertura insuficiente",
    "no_source": "Sin fuente configurada",
    "measurement_crosses_block": "Intervalos cruzados excluidos de la evolución",
    "outside_registered_history": "Período fuera del historial registrado",
    "filter_both": "Intervalo fuera de ambos límites del filtro",
    "unsupported_content": "Contenido no disponible en la fuente",
    "measured_total": "Total procedente de medición física",
    "before_operation": "Período anterior al inicio del registro",
    "unconfigured_period": "Período sin configuración",
    "partial_coverage": "Cobertura parcial",
    "missing_contributions": "Faltan contribuciones para el total",
    "calculation_configuration_changed": "Cambio de configuración dentro del intervalo; sin valor numérico",
    "pending_incorporation": "Total pendiente de incorporación",
    "no_calculation_basis": "Sin base para calcular el total",
    "detail_withdrawn": "Detalle retirado; total conservado",
    "filter_excludes_block": "Bloques no contenidos excluidos",
}


def quality_lines(snapshot):
    """Retain essential causes and exactCAT-01 source/basis periods, including same-mode configuration changes."""
    groups = defaultdict(list)
    for row in snapshot.energy_rows:
        for reason in row.reason_codes:
            groups[reason].append(row.category_id)
    lines = [
        REASONS.get(code, code) + ": " + ", ".join(categories)
        for code, categories in sorted(groups.items())
    ]
    general = snapshot.energy_rows[0]
    for segment in general.provenance_segments:
        origin = MODES[segment.source_mode]
        source = (
            str(segment.source_id)
            if segment.source_id
            else ", ".join(
                f"{b.category_id}/{b.source_id}" for b in segment.basis_sources
            )
            or "Sin base"
        )
        lines.append(
            f"{origin}: {segment.start.isoformat()} a {segment.end.isoformat()}; fuente/base {source}; revisión {segment.category_revision}."
        )
    lines.extend(snapshot.provenance)
    if not any(b.energy_kwh is not None for b in snapshot.chart_blocks):
        lines.append(
            "Evolución sin detalle disponible; el total conservado no se recalcula desde el gráfico."
        )
    if snapshot.provisional:
        lines.append("Período en curso: datos provisionales al corte indicado.")
    return lines or ["Sin limitaciones adicionales declaradas por las fuentes."]
