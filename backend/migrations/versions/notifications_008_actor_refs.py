"""008 registered actor FKs preserve historical account identity and complete fixture isolation by dependency."""

from alembic import op

revision = "notifications_008_actor_refs"
down_revision = "notifications_008_invariants"
branch_labels = None
depends_on = None


def upgrade():
    """Enforce actual006 actor identities; reject orphaned preexisting history rather than invent/backfill actors."""
    for table in ["notification_rule", "notification_rule_version"]:
        op.create_foreign_key(
            op.f("fk_" + table + "_created_by_identity_account"),
            table,
            "identity_account",
            ["created_by"],
            ["id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        )


def downgrade():
    """Remove own registered-actor references without altering006 accounts or protected notification rows."""
    for table in ["notification_rule", "notification_rule_version"]:
        op.drop_constraint(
            op.f("fk_" + table + "_created_by_identity_account"),
            table,
            type_="foreignkey",
        )
