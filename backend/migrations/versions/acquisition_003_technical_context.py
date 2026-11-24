"""003 owns durable context for adaptation evaluations and explicit native re-sends."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "acquisition_003_context"
down_revision = "consumption_002_context"
branch_labels = depends_on = None


def upgrade():
    """Keep native bytes, digests and historical contexts unchanged."""
    op.add_column(
        "acquisition_evaluation",
        sa.Column("technical_context", JSONB(), nullable=False, server_default="{}"),
    )


def downgrade():
    """Remove only003 operational metadata, preserving its evidence ledger."""
    op.drop_column("acquisition_evaluation", "technical_context")
