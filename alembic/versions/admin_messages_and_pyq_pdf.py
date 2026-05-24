"""admin user messages table and pyq reference pdf path

Revision ID: admin_msg_pyq_pdf_001
Revises: add_is_admin_001
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from app.db_migration_guards import has_column, has_index, has_table


revision = "admin_msg_pyq_pdf_001"
down_revision = "add_is_admin_001"
branch_labels = None
depends_on = None


def upgrade():
    if not has_table("admin_user_messages"):
        op.create_table(
            "admin_user_messages",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_admin_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
    if has_table("admin_user_messages") and not has_index("admin_user_messages", "ix_admin_user_messages_user_id"):
        op.create_index("ix_admin_user_messages_user_id", "admin_user_messages", ["user_id"])

    if has_table("pyqs") and not has_column("pyqs", "reference_pdf_path"):
        op.add_column(
            "pyqs",
            sa.Column("reference_pdf_path", sa.String(512), nullable=True),
        )


def downgrade():
    op.drop_column("pyqs", "reference_pdf_path")
    op.drop_index("ix_admin_user_messages_user_id", table_name="admin_user_messages")
    op.drop_table("admin_user_messages")
