"""008 bounded immutable response references for exact idempotent replay, without duplicating private payloads."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "notifications_008_receipts"
down_revision = "notifications_008_initial_window"
branch_labels = None
depends_on = None


def upgrade():
    """Add only status/revision/next-date metadata; configuration remains referenced by immutable version."""
    op.add_column(
        "notification_api_idempotency",
        sa.Column(
            "resource_metadata",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade():
    """Refuse removal of protected committed idempotency receipts."""
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS(SELECT 1 FROM notification_api_idempotency)")
    ):
        raise RuntimeError("Notification receipts are protected")
    op.drop_column("notification_api_idempotency", "resource_metadata")
