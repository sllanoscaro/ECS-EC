"""Presentation-only financial scopes copied from004: available subtotals and exact revision pairs stay separate."""

from ecs_ec.reports.formatting import money, number, percentage


def costs_lines(snapshot):
    """Describe effective closed cycles and each compatible available group without combining tax bases."""
    f = snapshot.financial_snapshot
    if not f.cycles:
        return ["Sin cierres de ciclo en este período."]
    lines = [
        f"{len(f.cycles)} ciclos por fecha de cierre; completos {f.complete_cycle_count}, parciales {f.partial_cycle_count}, no calculables {f.uncalculable_cycle_count}, fallidos {f.failed_cycle_count}."
    ]
    for total in f.available_totals:
        lines.append(
            f"Subtotal disponible · {total.code}: {money(total.amount, total.currency, total.tax_basis)}"
        )
    if not f.available_totals:
        lines.append("Costo no disponible; sin importes imputados.")
    for cycle in f.cycles:
        lines.append(
            f"Ciclo {cycle.start_at.date()} a {cycle.end_at.date()} · cierre {cycle.end_at.isoformat()}"
        )
    return lines


def comparison_lines(snapshot):
    """Render precisely the producer's paired subset and its exclusions; do not calculate differences here."""
    f = snapshot.financial_snapshot
    lines = []
    for total in f.comparison_totals:
        lines.append(
            f"{total.cycle_count} pares · {total.code} · {total.currency}/{total.tax_basis}: calculado {number(total.calculated)}, facturado comparable {number(total.billed)}, diferencia {number(total.delta_amount)}; porcentaje {percentage(total.delta_percent)}."
        )
    pending = sum(
        c.comparison_status == "missing_for_selected_revisions" for c in f.cycles
    )
    missing = sum(c.comparison_status == "no_bill" for c in f.cycles)
    if pending:
        lines.append(
            f"Contraste pendiente para estas revisiones: {pending} ciclos excluidos del contraste."
        )
    if missing:
        lines.append(f"Sin boleta: {missing} ciclos; no se inventa diferencia cero.")
    if not f.comparison_totals:
        lines.append(
            "Sin pares comparables; importe facturado y diferencia no disponibles."
        )
    for c in f.cycles:
        if c.bill:
            lines.append(
                f"Boleta ciclo {c.end_at.date()} · total a pagar {money(c.bill.total_payable, c.bill.currency, 'documento')}; distinto del facturado comparable."
            )
        if c.comparison:
            for line in c.comparison.excluded_lines:
                lines.append(
                    f"Exclusión: {line.code} · {number(line.amount)} {c.comparison.currency} · {line.reason_code}"
                )
    return lines
