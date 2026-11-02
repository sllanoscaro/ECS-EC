"""Exact pureCAT-01 candidates;002 alone incorporates them under its durable15-minute admission rule."""

from decimal import Decimal, localcontext

from ecs_ec.consumption.energy import exact_context
from ecs_ec.consumption.models import Contribution, Period, TotalCandidate
from ecs_ec.consumption.validation import covering_segments


class TotalCalculator:
    """Sum one accepted aligned contribution per configured partial, without replacing physical totals."""

    def evaluate(self, *, building_id, start, end, segments, contributions) -> TotalCandidate:
        """Return complete/incomplete/no_basis with immutable provenance; no clock, IO or side effects.

        Invalid objects raise ValueError; misaligned/missing/wrong-source references produce
        a missing-contributions diagnosis. Extra subintervals cannot manufacture alignment.
        """
        period = Period(start=start, end=end)
        selected = covering_segments(segments, period.start, period.end)
        first = selected[0]
        common = dict(building_id=building_id, start=period.start, end=period.end,
            configuration_revision=first.configuration_revision, category_revision=first.category_revision,
            configuration_segments=selected)
        if len({s.category_revision for s in selected}) > 1:
            return TotalCandidate(**(common | {"category_revision": None}), base_categories=(), contributions=(),
                energy_kwh=None, status="incomplete", reason_code="calculation_configuration_changed")
        if first.source_mode != "calculated":
            return TotalCandidate(**common, base_categories=(), contributions=(), energy_kwh=None, status="no_basis",
                reason_code="measured_total" if first.source_mode == "measured" else "no_calculation_basis")
        signatures = {(s.source_mode, s.source_id, s.base_categories, s.basis_category_revisions,
            tuple((b.category_id,b.source_id) for b in s.basis_sources)) for s in selected}
        if len(signatures) != 1: raise ValueError("inconsistent_category_revision")
        if len(first.basis_category_revisions) != len(first.base_categories):
            raise ValueError("basis_category_revisions_required")
        # Revalidate caller DTOs, including model_construct/model_copy attempts. Only
        # already-accepted physical evidence from002 is allowed through this boundary.
        parts = tuple(Contribution.model_validate(c.model_dump()) for c in contributions)
        included, missing = [], []
        expected_revisions = dict(zip(first.base_categories, first.basis_category_revisions, strict=False))
        for basis in first.basis_sources:
            observed = [c for c in parts if c.category_id == basis.category_id]
            exact = [c for c in observed if c.start == period.start and c.end == period.end
                and c.source_id == basis.source_id and (basis.category_id not in expected_revisions
                    or c.category_revision == expected_revisions[basis.category_id])]
            if len(exact) != 1 or len(observed) != 1: missing.append(basis.category_id)
            else: included.append(exact[0])
        if missing:
            return TotalCandidate(**common, base_categories=first.base_categories, contributions=tuple(included),
                energy_kwh=None, status="incomplete", missing_categories=tuple(missing), reason_code="missing_contributions")
        with localcontext(exact_context()):
            total = sum((c.energy_kwh for c in included), Decimal(0))
        return TotalCandidate(**common, base_categories=first.base_categories, contributions=tuple(included),
            energy_kwh=total, status="complete", reason_code=None)
