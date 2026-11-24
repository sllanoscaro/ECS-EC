"""002 persists trusted technical references outside the immutable native manifest."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "consumption_002_context"
down_revision = "reports_005_initial"
branch_labels = depends_on = None


def upgrade():
    """Leave historical attempts explicitly without context; never fabricate ancestry."""
    op.add_column(
        "reception_attempt",
        sa.Column("technical_context", JSONB(), nullable=False, server_default="{}"),
    )


def downgrade():
    """Remove only002 operational metadata; functional evidence is unaffected."""
    op.drop_column("reception_attempt", "technical_context")
