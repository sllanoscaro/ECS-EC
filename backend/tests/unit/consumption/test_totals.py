"""Total candidates require complete exact aligned contributions and stable source semantics."""

from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from ecs_ec.consumption.catalog_storage import configuration_segments
from ecs_ec.consumption.models import Contribution
from ecs_ec.consumption.totals import TotalCalculator
from backend.tests.unit.consumption.test_catalog import installation, revision
from backend.tests.unit.consumption.test_validation import START, END


def contribution(category=3, value="12", **changes):
    """Create one independently accepted partial reference, without acceptance or database writes."""
    return Contribution.model_validate(dict(measurement_id=UUID(int=category+100), measurement_revision=1,
        category_id=f"CAT-{category:02}", source_id=UUID(int=category), category_revision=1,
        energy_kwh=Decimal(value), start=START, end=END) | changes)


def evaluate(contributions=(), configs=None):
    """Evaluate syntheticCAT-01 history using the production calculator and exact caller interval."""
    return TotalCalculator().evaluate(building_id=UUID(int=99), start=START, end=END,
        segments=configuration_segments(configs or (revision(),), "CAT-01", START, END), contributions=contributions)


def test_complete_and_zero():
    """12+8 gives20; all-zero nonempty basis is complete and preserves every input reference."""
    parts = (contribution(), contribution(5, "8"))
    total = evaluate(parts)
    assert total.energy_kwh == Decimal(20) and total.status == "complete"
    assert total.base_categories == ("CAT-03", "CAT-05")
    assert total.contributions == parts
    assert evaluate((contribution(value="0"), contribution(5, "0"))).energy_kwh == 0


def test_empty_basis_and_physical_exclude_substitution():
    """Empty basis never yields zero; physical100 is not synthesized from partial60 or a missing total."""
    for config, reason in ((installation(()), "no_calculation_basis"), (installation(tuple(range(1,8))), "measured_total")):
        total = evaluate(tuple(contribution(i,"10") for i in range(2,8)), (revision(config),))
        assert total.energy_kwh is None and total.status == "no_basis" and total.reason_code == reason


@pytest.mark.parametrize("parts", [(contribution(),),
    (contribution(), contribution(5,"8", end=START.replace(minute=30))),
    (contribution(), contribution(5,"4", end=START.replace(minute=30)), contribution(5,"4", start=START.replace(minute=30))),
    (contribution(), contribution(5,"8", source_id=UUID(int=50))),
    (contribution(), contribution(5,"8"), contribution(5,"8")),
    (contribution(), contribution(5,"8", category_revision=2))])
def test_missing_invalid_or_misaligned_contribution(parts):
    """Never split/prorate, double count or accept evidence from the wrong source/revision."""
    total = evaluate(parts)
    assert total.status == "incomplete" and total.energy_kwh is None
    assert total.reason_code == "missing_contributions" and total.missing_categories == ("CAT-05",)


def test_recursive_or_outside_energy_rejected():
    """CAT-01 and invalid numeric contributions cannot masquerade as accepted physical partials."""
    for changes in (dict(category_id="CAT-01"), dict(energy_kwh="NaN"), dict(energy_kwh="-1")):
        with pytest.raises(ValidationError): contribution(**changes)


def test_maximum_six_individuals(scenarios):
    """Six literal M inputs sum to literal6*M, above the individual limit without rounding."""
    total = evaluate(tuple(contribution(i,scenarios["boundaries"]["M"]) for i in range(2,8)),
        (revision(installation(tuple(range(2,8)))),))
    assert total.status == "complete"
    assert total.energy_kwh == Decimal(scenarios["boundaries"]["six_M"])


def test_stable_global_change_and_changed_calculated_signature():
    """Cosmetic global revisions permit totals; source changes give segments, no fictitious missing/base."""
    first = revision()
    at = START.replace(minute=30)
    cosmetic = revision(installation(label="Renamed"), first, at)
    assert evaluate((contribution(), contribution(5,"8")), (first, cosmetic)).energy_kwh == 20
    for config in (installation(**{"3":UUID(int=30)}), installation((3,)), installation((1,3,5))):
        changed = revision(config, first, at)
        total = evaluate((contribution(), contribution(5,"8")), (first, changed))
        assert total.reason_code == "calculation_configuration_changed" and total.category_revision is None
        assert total.energy_kwh is None and total.base_categories == () and total.contributions == ()
        assert total.missing_categories == () and len(total.configuration_segments) == 2
