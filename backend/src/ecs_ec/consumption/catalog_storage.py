"""PostgreSQL storage for001 installation history only; no readings, admission or retention tables."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, select, text
from sqlalchemy.orm import Mapped, mapped_column

from ecs_ec.consumption.catalog import CATEGORY_IDS
from ecs_ec.consumption.models import CategorySource, InstallationRevision, Period
from ecs_ec.core.database import Base


class BuildingRow(Base):
    """Provisioned singleton; this row is the first shared configuration/reception lock."""

    __tablename__ = "consumption_building"
    __table_args__ = (CheckConstraint("singleton = 1", name="singleton"), UniqueConstraint("singleton"))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    singleton: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CategoryRow(Base):
    """Fixed seven catalog entries, also used for stable ordered category coordination."""

    __tablename__ = "consumption_category"
    __table_args__ = (CheckConstraint("id IN ('CAT-01','CAT-02','CAT-03','CAT-04','CAT-05','CAT-06','CAT-07')", name="fixed_id"),
        CheckConstraint("display_order BETWEEN 1 AND 7", name="display_order"), UniqueConstraint("display_order"))
    id: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(String(300))
    display_order: Mapped[int] = mapped_column(Integer)


class MeasurementSourceRow(Base):
    """Stable source UUID and original descriptive label, retained after deactivation."""

    __tablename__ = "consumption_source"
    __table_args__ = (CheckConstraint("length(trim(label)) > 0", name="nonempty_label"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(ForeignKey("consumption_building.id", ondelete="RESTRICT"))
    label: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InstallationRow(Base):
    """Immutable global revision with actor/zone/times; effective_until is derived on reads."""

    __tablename__ = "consumption_installation"
    __table_args__ = (UniqueConstraint("building_id", "revision", name="uq_consumption_installation_revision"),
        UniqueConstraint("building_id", "effective_from", name="uq_consumption_installation_effective"),
        CheckConstraint("revision > 0", name="positive_revision"),
        CheckConstraint("effective_from <= recorded_at", name="effective_not_future"))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(ForeignKey("consumption_building.id", ondelete="RESTRICT"))
    revision: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(100))


class CategorySourceRow(Base):
    """Seven source snapshots per installation, preserving labels and per-category revisions."""

    __tablename__ = "consumption_category_source"
    __table_args__ = (UniqueConstraint("installation_revision_id", "source_id"),
        CheckConstraint("category_revision > 0", name="positive_revision"),
        CheckConstraint("(has_meter AND source_id IS NOT NULL AND source_label IS NOT NULL AND length(trim(source_label)) > 0) OR (NOT has_meter AND source_id IS NULL AND source_label IS NULL)", name="source_presence"))
    installation_revision_id: Mapped[UUID] = mapped_column(ForeignKey("consumption_installation.id", ondelete="RESTRICT"), primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("consumption_category.id", ondelete="RESTRICT"), primary_key=True)
    has_meter: Mapped[bool] = mapped_column(Boolean)
    source_id: Mapped[UUID | None] = mapped_column(ForeignKey("consumption_source.id", ondelete="RESTRICT"), nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category_revision: Mapped[int] = mapped_column(Integer)


async def lock_configuration(unit_of_work, building_id, category_ids=CATEGORY_IDS):
    """Acquire context then sorted catalog locks in READ COMMITTED;002 must use this same order/UoW.

    Call before resolving configuration/history or changing incorporation bounds. Return
    None when unprovisioned. Locks last until the caller's commit/rollback, never Python locks.
    """
    if await unit_of_work.session.scalar(text("SHOW transaction_isolation")) != "read committed":
        raise ValueError("configuration_requires_read_committed")
    row = await unit_of_work.session.scalar(select(BuildingRow).where(BuildingRow.id == building_id).with_for_update())
    if row is not None:
        await unit_of_work.session.execute(select(CategoryRow.id).where(CategoryRow.id.in_(category_ids))
            .order_by(CategoryRow.id).with_for_update())
    return row


async def read_revisions(unit_of_work, building_id):
    """Read full immutable configuration snapshots in the caller's transaction, ordered by revision."""
    revisions = (await unit_of_work.session.scalars(select(InstallationRow)
        .where(InstallationRow.building_id == building_id).order_by(InstallationRow.revision))).all()
    if not revisions: return ()
    rows = (await unit_of_work.session.scalars(select(CategorySourceRow)
        .where(CategorySourceRow.installation_revision_id.in_([r.id for r in revisions]))
        .order_by(CategorySourceRow.category_id))).all()
    grouped = {r.id: [] for r in revisions}
    for row in rows:
        grouped[row.installation_revision_id].append(CategorySource(category_id=row.category_id,
            has_meter=row.has_meter, source_id=row.source_id, source_label=row.source_label,
            category_revision=row.category_revision))
    return tuple(InstallationRevision(id=r.id, building_id=r.building_id, revision=r.revision,
        effective_from=r.effective_from, recorded_at=r.recorded_at, created_by=r.created_by,
        timezone=r.timezone, categories=tuple(grouped[r.id])) for r in revisions)


def configuration_segments(revisions, category_id, start, end):
    """Derive intersecting segments from consecutive effective times, leaving unconfigured gaps explicit."""
    period = Period(start=start, end=end)
    segments = []
    for index, revision in enumerate(revisions):
        lower = max(period.start, revision.effective_from)
        upper = min(period.end, revisions[index + 1].effective_from) if index + 1 < len(revisions) else period.end
        if lower < upper: segments.append(revision.segment(category_id, lower, upper))
    return tuple(segments)


async def append_revision(unit_of_work, revision):
    """Flush one configuration and its seven states; preserve earlier snapshots and never commit."""
    unit_of_work.session.add(InstallationRow(**revision.model_dump(exclude={"categories"})))
    await unit_of_work.session.flush()
    for entry in revision.categories:
        unit_of_work.session.add(CategorySourceRow(installation_revision_id=revision.id, **entry.model_dump()))
    await unit_of_work.session.flush()
