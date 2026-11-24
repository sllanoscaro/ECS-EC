"""005 six mandatory sections assembled exclusively from the confirmed immutable projection."""

from ecs_ec.reports.financial_summary import costs_lines, comparison_lines
from ecs_ec.reports.quality import quality_lines


def sections(snapshot):
    """Return financial/quality text without altering producer values or selected financial pairs."""
    return dict(
        costs=costs_lines(snapshot),
        comparison=comparison_lines(snapshot),
        quality=quality_lines(snapshot),
    )
