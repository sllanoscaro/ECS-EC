"""008 persist the next resolved nominal slot so an overdue cut survives a tzdata upgrade unchanged."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "notifications_008_calendar_slot"
down_revision = "notifications_008_actor_refs"
branch_labels = None
depends_on = None


def upgrade():
    """Add owned future-slot metadata only; immutable occurrences and foreign owner tables remain untouched."""
    op.add_column(
        "notification_activation", sa.Column("next_slot", JSONB, nullable=True)
    )


def downgrade():
    """Refuse to discard recorded scheduling intent while any activation survives."""
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS(SELECT 1 FROM notification_activation)")
    ):
        raise RuntimeError("Notification scheduling history is protected")
    op.drop_column("notification_activation", "next_slot")
