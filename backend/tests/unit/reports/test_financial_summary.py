"""005 formatting consumes producer subtotals/pairs as supplied, keeping incompatible bases separate."""

from types import SimpleNamespace as N
from ecs_ec.reports.financial_summary import costs_lines, comparison_lines
from ecs_ec.reports.formatting import money


def test_available_sixty_and_exact_paired_forty_thirty_eight_two():
    """Presentation does not substitute the larger available scope for the producer's two-pair subset."""
    cycles = [
        N(
            start_at=N(date=lambda: "2026-01-01"),
            end_at=N(
                date=lambda: "2026-01-02", isoformat=lambda: "2026-01-02T00:00:00Z"
            ),
            comparison_status="available" if i != 1 else "no_bill",
            comparison=None,
            bill=None,
        )
        for i in range(3)
    ]
    source = N(
        financial_snapshot=N(
            cycles=cycles,
            complete_cycle_count=3,
            partial_cycle_count=0,
            uncalculable_cycle_count=0,
            failed_cycle_count=0,
            available_totals=[
                N(code="energy", amount="60", currency="CLP", tax_basis="neto")
            ],
            comparison_totals=[
                N(
                    cycle_count=2,
                    code="energy",
                    currency="CLP",
                    tax_basis="neto",
                    calculated="40",
                    billed="38",
                    delta_amount="2",
                    delta_percent=None,
                )
            ],
        )
    )
    assert "60 CLP (neto)" in " ".join(costs_lines(source))
    text = " ".join(comparison_lines(source))
    assert (
        "2 pares" in text
        and "calculado 40" in text
        and "comparable 38" in text
        and "diferencia 2" in text
    )
    assert "No aplicable" in text and "Sin boleta: 1" in text


def test_unknown_difference_and_signed_currency_basis():
    """Pending revisions cannot fabricate a zero difference; money keeps the exact producer sign and tax basis."""
    source = N(
        financial_snapshot=N(
            cycles=[
                N(
                    comparison_status="missing_for_selected_revisions",
                    comparison=None,
                    bill=None,
                )
            ],
            comparison_totals=[],
        )
    )
    text = " ".join(comparison_lines(source))
    assert (
        "Contraste pendiente para estas revisiones" in text
        and "diferencia no disponibles" in text
    )
    assert money("-9", "CLP", "neto") == "-9 CLP (neto)"
    assert money("9", "CLP", "bruto") != "9 CLP (neto)"
