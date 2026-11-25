"""008 enforce immutable history and deferred graph membership; shared owner tables remain unchanged."""

import sqlalchemy as sa
from alembic import op

revision = "notifications_008_invariants"
down_revision = "notifications_008_receipts"
branch_labels = None
depends_on = None


SQL = r"""
CREATE FUNCTION notification_008_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
   IF OLD.retain_until>clock_timestamp() THEN RAISE EXCEPTION 'protected notification history' USING ERRCODE='23514'; END IF;
   RETURN OLD;
 END IF;
 IF (to_jsonb(NEW)-'retain_until'-'retired_at') IS DISTINCT FROM (to_jsonb(OLD)-'retain_until'-'retired_at')
 OR NEW.retain_until<OLD.retain_until THEN
   RAISE EXCEPTION 'immutable notification history' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION notification_008_definition_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='UPDATE' AND to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD) THEN RAISE EXCEPTION 'immutable notification definition' USING ERRCODE='23514'; END IF;
 IF TG_OP='DELETE' AND EXISTS(SELECT 1 FROM notification_rule_version WHERE id=OLD.version_id AND retain_until>clock_timestamp()) THEN RAISE EXCEPTION 'protected notification definition' USING ERRCODE='23514'; END IF;
 RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE FUNCTION notification_008_graph() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='notification_rule' THEN
   IF NOT EXISTS(SELECT 1 FROM notification_rule_version WHERE id=NEW.current_version_id AND rule_id=NEW.id) THEN RAISE EXCEPTION 'invalid notification version owner' USING ERRCODE='23514'; END IF;
 ELSIF TG_TABLE_NAME='notification_schedule' THEN
   IF NOT EXISTS(SELECT 1 FROM notification_rule_version WHERE id=NEW.version_id AND schedule_id=NEW.id AND mode='periodica') THEN RAISE EXCEPTION 'invalid notification schedule owner' USING ERRCODE='23514'; END IF;
 ELSIF TG_TABLE_NAME='notification_condition' THEN
   IF NOT EXISTS(SELECT 1 FROM notification_rule_version WHERE id=NEW.version_id AND condition_id=NEW.id AND mode='urgente') THEN RAISE EXCEPTION 'invalid notification condition owner' USING ERRCODE='23514'; END IF;
 ELSIF TG_TABLE_NAME='notification_recovery_member' THEN
   IF NOT EXISTS(SELECT 1 FROM notification_delivery d JOIN notification_message m ON m.id=d.message_id JOIN notification_occurrence o ON o.id=m.occurrence_id JOIN notification_delivery r ON r.id=NEW.recovery_delivery_id JOIN notification_message rm ON rm.id=r.message_id JOIN notification_occurrence ro ON ro.id=rm.occurrence_id WHERE d.id=NEW.original_delivery_id AND d.id<>r.id AND d.attempt_count=0 AND d.state='cancelada' AND d.cancellation_reason='consolidada_en_recuperacion' AND o.kind='periodica' AND ro.kind='recuperacion' AND o.version_id=ro.version_id AND d.account_id=r.account_id) THEN RAISE EXCEPTION 'invalid notification recovery membership' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
"""


def upgrade():
    """Attach only008 triggers, deferring graph checks until all referenced owned rows are flushed."""
    op.execute(SQL)
    for table in [
        "notification_rule_version",
        "notification_message",
        "notification_evidence",
    ]:
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION notification_008_immutable()"
        )
    for table in [
        "notification_schedule",
        "notification_condition",
        "notification_version_recipient",
    ]:
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION notification_008_definition_immutable()"
        )
    for table in [
        "notification_rule",
        "notification_schedule",
        "notification_condition",
        "notification_recovery_member",
    ]:
        op.execute(
            f"CREATE CONSTRAINT TRIGGER {table}_graph AFTER INSERT OR UPDATE ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION notification_008_graph()"
        )


def downgrade():
    """Refuse weakening protection while any notification history exists."""
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM notification_rule)")):
        raise RuntimeError("Notification history is protected")
    for table in [
        "notification_rule",
        "notification_schedule",
        "notification_condition",
        "notification_recovery_member",
    ]:
        op.execute(f"DROP TRIGGER {table}_graph ON {table}")
    for table in [
        "notification_rule_version",
        "notification_message",
        "notification_evidence",
        "notification_schedule",
        "notification_condition",
        "notification_version_recipient",
    ]:
        op.execute(f"DROP TRIGGER {table}_immutable ON {table}")
    for function in [
        "notification_008_immutable",
        "notification_008_definition_immutable",
        "notification_008_graph",
    ]:
        op.execute("DROP FUNCTION " + function + "()")
