"""Fixed FR-001 catalog and pure global/category revision derivation."""

from uuid import uuid4

from ecs_ec.consumption.models import CategorySource, ConsumptionCategory, InstallationRevision

CATEGORIES = tuple(ConsumptionCategory(id=f"CAT-{i:02}", name=name, scope=scope, display_order=i)
    for i, (name, scope) in enumerate((
        ("Energía eléctrica total", "Total medido directamente o calculado desde las categorías presentes, con procedencia y alcance identificados."),
        ("HVAC y agua caliente sanitaria", "Calefacción, ventilación, aire acondicionado y agua caliente sanitaria en una serie conjunta."),
        ("Iluminación exterior", "Consumo eléctrico de iluminación exterior."),
        ("Iluminación interior", "Consumo eléctrico de iluminación interior."),
        ("Circuitos de enchufes", "Consumo eléctrico de los circuitos de enchufes."),
        ("Sistema sanitario", "Consumo eléctrico de los sistemas de agua potable y alcantarillado."),
        ("Ascensores", "Consumo eléctrico de los ascensores."),
    ), 1))
CATEGORY_IDS = tuple(c.id for c in CATEGORIES)


def category_signature(categories, category_id):
    """Identify actual source semantics, excluding labels, global revisions and unrelated categories."""
    entry = next(s for s in categories if s.category_id == category_id)
    if entry.has_meter: return ("measured", entry.source_id)
    if category_id != "CAT-01": return ("unavailable",)
    basis = tuple((s.category_id, s.source_id) for s in sorted(categories, key=lambda s: s.category_id)
                  if s.category_id != "CAT-01" and s.has_meter)
    return ("calculated", basis) if basis else ("unavailable",)


def make_revision(request, *, building_id, previous, effective_from, recorded_at, actor_ref):
    """Derive immutable snapshots; only changed category signatures increment their local revision."""
    states = []
    for entry in sorted(request.categories, key=lambda s: s.category_id):
        revision = 1 if previous is None else previous.entry(entry.category_id).category_revision + int(
            category_signature(previous.categories, entry.category_id) != category_signature(request.categories, entry.category_id))
        states.append(CategorySource(**entry.model_dump(), category_revision=revision))
    return InstallationRevision(id=uuid4(), building_id=building_id, revision=1 if previous is None else previous.revision + 1,
        effective_from=effective_from, recorded_at=recorded_at, created_by=actor_ref,
        timezone=request.timezone, categories=tuple(states))
