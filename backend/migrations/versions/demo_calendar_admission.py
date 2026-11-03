"""Persist explicit local demo calendar admission while retaining the strict900s default."""
from alembic import op
import sqlalchemy as sa

revision = 'demo_calendar_admission'
down_revision = 'f68f086ee8a7'
branch_labels = None
depends_on = None


def upgrade():
    """Add an opt-in calendar flag; existing rows retain the exact900-second invariant."""
    op.add_column('category_reception_state', sa.Column('calendar_admission', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.drop_constraint(op.f('ck_category_reception_state_admission'), 'category_reception_state', type_='check')
    op.create_check_constraint('admission', 'category_reception_state', "(last_new_data_at IS NULL AND next_admissible_at IS NULL AND latest_interval_end IS NULL) OR (last_new_data_at IS NOT NULL AND latest_interval_end IS NOT NULL AND ((NOT calendar_admission AND next_admissible_at = last_new_data_at + interval '900 seconds') OR (calendar_admission AND next_admissible_at > last_new_data_at AND next_admissible_at <= last_new_data_at + interval '900 seconds' AND mod(extract(epoch from next_admissible_at),900)=0)))")


def downgrade():
    """Refuse removal while calendar-mode evidence exists; never rewrite historical reception timestamps."""
    connection = op.get_bind()
    if connection.scalar(sa.text('SELECT count(*) FROM category_reception_state WHERE calendar_admission')):
        raise RuntimeError('calendar_state_requires_verified_restore')
    op.drop_constraint(op.f('ck_category_reception_state_admission'), 'category_reception_state', type_='check')
    op.drop_column('category_reception_state', 'calendar_admission')
    op.create_check_constraint('admission', 'category_reception_state', "(last_new_data_at IS NULL AND next_admissible_at IS NULL AND latest_interval_end IS NULL) OR (last_new_data_at IS NOT NULL AND next_admissible_at = last_new_data_at + interval '900 seconds' AND latest_interval_end IS NOT NULL)")
