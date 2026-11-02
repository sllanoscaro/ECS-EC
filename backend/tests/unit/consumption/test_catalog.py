"""Catalog names, physical presence and category-specific configuration identity."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from ecs_ec.consumption.catalog import CATEGORIES, category_signature, make_revision
from ecs_ec.consumption.models import ConfigurationInput


def installation(present=(3, 5), *, label="Synthetic meter", timezone="America/Santiago", **changes):
    """Return a complete synthetic installation; overrides are per-category source UUIDs."""
    return ConfigurationInput(expected_revision=0, timezone=timezone, effective_from="2025-01-01T00:00:00Z",
        categories=[dict(category_id=f"CAT-{i:02}", has_meter=i in present,
            source_id=changes.get(str(i), UUID(int=i)) if i in present else None,
            source_label=label if i in present else None) for i in range(1, 8)])


def revision(config=None, previous=None, at=None):
    """Create a domain snapshot at a controlled instant, without database or acceptance."""
    return make_revision(config or installation(), building_id=UUID(int=99), previous=previous,
                         effective_from=at or datetime(2025, 1, 1, tzinfo=UTC),
                         recorded_at=datetime(2026, 1, 1, tzinfo=UTC), actor_ref="process:test")


def test_fixed_catalog_and_basis():
    """Seven ordered names/scopes stay independent from any installed subset."""
    assert [c.id for c in CATEGORIES] == [f"CAT-{i:02}" for i in range(1, 8)]
    assert [c.display_order for c in CATEGORIES] == list(range(1, 8))
    assert [c.name for c in CATEGORIES] == ["Energía eléctrica total", "HVAC y agua caliente sanitaria",
        "Iluminación exterior", "Iluminación interior", "Circuitos de enchufes", "Sistema sanitario", "Ascensores"]
    assert "eléctrico" in CATEGORIES[5].scope
    assert revision().segment("CAT-01", datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)).base_categories == ("CAT-03", "CAT-05")
    assert category_signature(installation(()).categories, "CAT-01") == ("unavailable",)


def test_category_revisions_change_only_with_signature():
    """Labels/other categories preserve identity; returning to a source increments again."""
    first = revision()
    labels = revision(installation(label="Renamed"), first)
    assert [c.category_revision for c in labels.categories] == [1] * 7
    changed = revision(installation(**{"3": UUID(int=30)}), labels)
    assert changed.entry("CAT-01").category_revision == 2
    assert changed.entry("CAT-03").category_revision == 2
    assert changed.entry("CAT-05").category_revision == 1
    restored = revision(installation(), changed)
    assert restored.entry("CAT-03").category_revision == 3
    physical = revision(installation((1, 3, 5)))
    other = revision(installation((1, 3, 5), **{"3": UUID(int=30)}), physical)
    assert other.entry("CAT-01").category_revision == 1
    assert other.entry("CAT-03").category_revision == 2


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "reused", "null_source", "label_without_meter", "timezone", "derived_revision"])
def test_invalid_installations(mutation):
    """Reject incomplete/ambiguous installations before any storage effects."""
    values = installation().model_dump()
    values["categories"] = list(values["categories"])
    if mutation == "missing": values["categories"].pop()
    if mutation == "duplicate": values["categories"][0] = values["categories"][1]
    if mutation == "reused": values["categories"][4]["source_id"] = values["categories"][2]["source_id"]
    if mutation == "null_source": values["categories"][2]["source_id"] = None
    if mutation == "label_without_meter": values["categories"][0]["source_label"] = "invalid"
    if mutation == "timezone": values["timezone"] = "Unknown/Zone"
    if mutation == "derived_revision": values["categories"][2]["category_revision"] = 8
    with pytest.raises(ValidationError): ConfigurationInput.model_validate(values)
