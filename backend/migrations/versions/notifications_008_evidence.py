"""008 normalize exact nullable energy/provenance and protect completed attempt evidence."""

import sqlalchemy as sa
from alembic import op

revision = "notifications_008_evidence"
down_revision = "notifications_008_calendar_slot"
branch_labels = None
depends_on = None


def upgrade():
    """Add typed evidence fields without importing mutable metadata or changing another owner's tables."""
    op.execute("""ALTER TABLE notification_evidence
      ADD COLUMN value_kwh NUMERIC NULL,
      ADD COLUMN origin VARCHAR(20) NOT NULL DEFAULT 'sin_fuente',
      ADD COLUMN limitation_code VARCHAR(100) NULL DEFAULT 'informacion_insuficiente',
      ADD COLUMN category_id VARCHAR(6) NULL,
      ADD COLUMN window_start TIMESTAMPTZ NULL,
      ADD COLUMN window_end TIMESTAMPTZ NULL,
      ADD COLUMN cutoff_at TIMESTAMPTZ NULL,
      ADD COLUMN source_refs JSONB NOT NULL DEFAULT '[]',
      ADD CONSTRAINT ck_notification_evidence_origin CHECK(origin IN ('medido','calculado','sin_fuente')),
      ADD CONSTRAINT ck_notification_evidence_energy CHECK(value_kwh IS NULL OR (value_kwh>=0 AND value_kwh::text NOT IN ('NaN','Infinity','-Infinity'))),
      ADD CONSTRAINT ck_notification_evidence_absence CHECK(value_kwh IS NOT NULL OR limitation_code IS NOT NULL),
      ADD CONSTRAINT ck_notification_evidence_window CHECK((window_start IS NULL AND window_end IS NULL) OR window_start<window_end)""")
    for table in ("notification_episode", "notification_evaluation_state"):
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_scope CHECK(scope_key ~ '^CAT-0[1-7]$' OR scope_key IN ('recepcion_rechazada','calculo_fallido','pdf_fallido'))"
        )
    op.execute("""CREATE FUNCTION notification_008_attempt_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
       IF TG_OP='DELETE' THEN
        IF OLD.retain_until>clock_timestamp() THEN RAISE EXCEPTION 'protected notification attempt' USING ERRCODE='23514'; END IF;
        RETURN OLD;
       END IF;
       IF NEW.retain_until<OLD.retain_until OR
       (OLD.outcome IS NOT NULL AND (to_jsonb(NEW)-'retain_until') IS DISTINCT FROM (to_jsonb(OLD)-'retain_until')) OR
       (OLD.outcome IS NULL AND (to_jsonb(NEW)-ARRAY['finished_at','outcome','functional_reason_code','acceptance_confirmed_at','relay_reference','retain_until']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['finished_at','outcome','functional_reason_code','acceptance_confirmed_at','relay_reference','retain_until'])) THEN
        RAISE EXCEPTION 'immutable notification attempt' USING ERRCODE='23514';
       END IF;
       RETURN NEW;
      END $$""")
    op.execute(
        "CREATE TRIGGER notification_attempt_immutable BEFORE UPDATE OR DELETE ON notification_delivery_attempt FOR EACH ROW EXECUTE FUNCTION notification_008_attempt_immutable()"
    )
    for table in ("notification_occurrence", "notification_evaluation"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION notification_008_immutable()"
        )


def downgrade():
    """A nonempty installation cannot lose captured evidence or its immutability protections."""
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM notification_rule)")):
        raise RuntimeError("Notification history is protected")
    for table in ("notification_occurrence", "notification_evaluation"):
        op.execute(f"DROP TRIGGER {table}_immutable ON {table}")
    op.execute(
        "DROP TRIGGER notification_attempt_immutable ON notification_delivery_attempt"
    )
    op.execute("DROP FUNCTION notification_008_attempt_immutable()")
    for table in ("notification_episode", "notification_evaluation_state"):
        op.drop_constraint(op.f(f"ck_{table}_scope"), table, type_="check")
    for name in ("origin", "energy", "absence", "window"):
        op.drop_constraint(
            op.f("ck_notification_evidence_" + name),
            "notification_evidence",
            type_="check",
        )
    for column in (
        "value_kwh",
        "origin",
        "limitation_code",
        "category_id",
        "window_start",
        "window_end",
        "cutoff_at",
        "source_refs",
    ):
        op.drop_column("notification_evidence", column)
