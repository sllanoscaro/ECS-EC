"""005 presentation labels; energy and configuration segments remain the producer's original values."""

from ecs_ec.reports.formatting import number, percentage

MODES = {
    "measured": "Medido",
    "calculated": "Calculado",
    "mixed": "Origen mixto",
    "unavailable": "Sin fuente",
}
STATES = {
    "available": "Disponible",
    "incomplete": "Incompleto",
    "no_data": "Sin datos",
    "no_meter": "Sin medidor",
}


def table_rows(snapshot):
    """Return all seven categories without dropping missing/zero/estimated-source distinctions."""
    return [
        (
            f"{r.category_id} · {r.name}",
            number(r.energy_kwh),
            percentage(r.coverage_percent),
            MODES[r.source_mode],
            STATES.get(r.state, r.state),
        )
        for r in snapshot.energy_rows
    ]
