"""008 acknowledge durable event identities instead of treating timestamp order as commit order."""

import sqlalchemy as sa
from alembic import op

revision = "notifications_008_consumed"
down_revision = "notifications_008_evidence"
branch_labels = None
depends_on = None


def upgrade():
    """Install one owned restrictive acknowledgement ledger, atomic with consumer transitions."""
    op.execute("""CREATE TABLE notification_consumed_event(
      activation_id UUID NOT NULL REFERENCES notification_activation(id) ON DELETE RESTRICT,
      source_event_id UUID NOT NULL REFERENCES functional_event(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      recorded_by VARCHAR(200) NOT NULL,
      retain_until TIMESTAMPTZ NOT NULL CHECK(retain_until>created_at),
      PRIMARY KEY(activation_id,source_event_id))""")
    op.execute(
        "CREATE TRIGGER notification_consumed_event_immutable BEFORE UPDATE OR DELETE ON notification_consumed_event FOR EACH ROW EXECUTE FUNCTION notification_008_immutable()"
    )


def downgrade():
    """A populated event ledger cannot lose its acknowledgement or protected source links."""
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS(SELECT 1 FROM notification_consumed_event)")
    ):
        raise RuntimeError("Notification event history is protected")
    op.drop_table("notification_consumed_event")
