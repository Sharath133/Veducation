"""add support_tickets and user_feedback tables

Revision ID: support_fb_002
Revises: add_is_admin_001
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.db_migration_guards import has_index, has_table

revision = "support_fb_002"
down_revision = "add_is_admin_001"
branch_labels = None
depends_on = None


def upgrade():
    if not has_table("support_tickets"):
        op.create_table(
            "support_tickets",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("subject", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if has_table("support_tickets"):
        if not has_index("support_tickets", "ix_support_tickets_user_id"):
            op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"], unique=False)
        if not has_index("support_tickets", "ix_support_tickets_status"):
            op.create_index("ix_support_tickets_status", "support_tickets", ["status"], unique=False)

    if not has_table("user_feedback"):
        op.create_table(
            "user_feedback",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False, server_default="suggestion"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if has_table("user_feedback"):
        if not has_index("user_feedback", "ix_user_feedback_user_id"):
            op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"], unique=False)
        if not has_index("user_feedback", "ix_user_feedback_category"):
            op.create_index("ix_user_feedback_category", "user_feedback", ["category"], unique=False)


def downgrade():
    op.drop_index("ix_user_feedback_category", table_name="user_feedback")
    op.drop_index("ix_user_feedback_user_id", table_name="user_feedback")
    op.drop_table("user_feedback")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_user_id", table_name="support_tickets")
    op.drop_table("support_tickets")
