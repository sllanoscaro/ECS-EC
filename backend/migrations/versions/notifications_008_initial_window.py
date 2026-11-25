"""008 user-approved explicitly empty initial periodic window, isolated from all other domain intervals."""

from hashlib import sha256

import sqlalchemy as sa
from alembic import op

revision = "notifications_008_initial_window"
down_revision = "notifications_008_initial"
branch_labels = None
depends_on = None


def upgrade():
    """Permit only identified empty periodic cuts; urgent and evaluation windows remain strictly positive."""
    op.add_column(
        "notification_occurrence",
        sa.Column(
            "initial_window_empty",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    name = (
        "ck_notification_occurrence_c_"
        + sha256(
            "(window_start IS NULL AND window_end IS NULL) OR window_start<window_end".encode()
        ).hexdigest()[:12]
    )
    op.drop_constraint(op.f(name), "notification_occurrence", type_="check")
    op.create_check_constraint(
        "window",
        "notification_occurrence",
        "(window_start IS NULL AND window_end IS NULL AND NOT initial_window_empty) OR window_start<window_end OR (kind='periodica' AND initial_window_empty AND window_start=window_end)",
    )


def downgrade():
    """Refuse incompatible historical empty windows rather than delete or rewrite approved evidence."""
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM notification_occurrence WHERE initial_window_empty)"
        )
    ):
        raise RuntimeError("Initial window history is protected")
    op.drop_constraint(
        op.f("ck_notification_occurrence_window"),
        "notification_occurrence",
        type_="check",
    )
    name = (
        "ck_notification_occurrence_c_"
        + sha256(
            "(window_start IS NULL AND window_end IS NULL) OR window_start<window_end".encode()
        ).hexdigest()[:12]
    )
    op.create_check_constraint(
        op.f(name),
        "notification_occurrence",
        "(window_start IS NULL AND window_end IS NULL) OR window_start<window_end",
    )
    op.drop_column("notification_occurrence", "initial_window_empty")
