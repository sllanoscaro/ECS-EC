"""005 quality/formatting keeps absence, zero, small positives and simulator provenance distinct."""

from backend.tests.support.report_snapshot import snapshot
from ecs_ec.reports.energy_table import table_rows
from ecs_ec.reports.quality import quality_lines
from ecs_ec.reports.formatting import number, percentage


def test_zero_absence_and_exact_small_value():
    """Nullable energy cannot become zero, including under display rounding of percentages only."""
    rows = table_rows(snapshot(value="0"))
    assert (
        rows[0][1] == "0"
        and rows[-1][1] == "No disponible"
        and rows[-1][-1] == "Sin medidor"
    )
    assert number("0.000001") == "0.000001" and percentage("0.000001") == "<0.01 %"
    assert percentage(None) == "No aplicable" and number("-2") == "-2"


def test_retired_chart_and_explicit_simulation():
    """A retained1200 total is independent of missing chart detail and trusted synthetic provenance stays visible."""
    source = snapshot(value="1200").model_copy(
        update={
            "provenance": (
                "Origen simulado identificado en la configuración de fuentes.",
            )
        }
    )
    text = " ".join(quality_lines(source))
    assert (
        source.energy_rows[0].energy_kwh == "1200"
        and "no se recalcula" in text
        and "simulado" in text
    )
