"""add free_duel_entry_credits to users

Revision ID: loyalty_free_entry_002
Revises: add_is_admin_001
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa

from app.db_migration_guards import has_column

revision = "loyalty_free_entry_002"
down_revision = "add_is_admin_001"
branch_labels = None
depends_on = None


def upgrade():
    if not has_column("users", "free_duel_entry_credits"):
        op.add_column(
            "users",
            sa.Column(
                "free_duel_entry_credits",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade():
    op.drop_column("users", "free_duel_entry_credits")
