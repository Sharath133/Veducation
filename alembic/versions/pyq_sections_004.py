"""pyq category sections and section pdfs

Revision ID: pyq_sections_004
Revises: merge_four_heads_003
Create Date: 2026-05-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from app.db_migration_guards import has_index, has_table


revision = "pyq_sections_004"
down_revision = "merge_four_heads_003"
branch_labels = None
depends_on = None


def upgrade():
    if not has_table("pyq_categories"):
        op.create_table(
            "pyq_categories",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("title", sa.String(120), nullable=False),
            sa.Column("icon", sa.String(50), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("code"),
        )
    if not has_index("pyq_categories", "ix_pyq_categories_code"):
        op.create_index("ix_pyq_categories_code", "pyq_categories", ["code"])
    if not has_index("pyq_categories", "ix_pyq_categories_is_active"):
        op.create_index("ix_pyq_categories_is_active", "pyq_categories", ["is_active"])

    if not has_table("pyq_sections"):
        op.create_table(
            "pyq_sections",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("pyq_categories.id"), nullable=False),
            sa.Column("title", sa.String(160), nullable=False),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
    if not has_index("pyq_sections", "ix_pyq_sections_category_id"):
        op.create_index("ix_pyq_sections_category_id", "pyq_sections", ["category_id"])
    if not has_index("pyq_sections", "ix_pyq_sections_is_active"):
        op.create_index("ix_pyq_sections_is_active", "pyq_sections", ["is_active"])

    if not has_table("pyq_section_pdfs"):
        op.create_table(
            "pyq_section_pdfs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("section_id", UUID(as_uuid=True), sa.ForeignKey("pyq_sections.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("file_path", sa.String(512), nullable=False),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
    if not has_index("pyq_section_pdfs", "ix_pyq_section_pdfs_section_id"):
        op.create_index("ix_pyq_section_pdfs_section_id", "pyq_section_pdfs", ["section_id"])
    if not has_index("pyq_section_pdfs", "ix_pyq_section_pdfs_is_active"):
        op.create_index("ix_pyq_section_pdfs_is_active", "pyq_section_pdfs", ["is_active"])


def downgrade():
    if has_table("pyq_section_pdfs"):
        op.drop_index("ix_pyq_section_pdfs_is_active", table_name="pyq_section_pdfs")
        op.drop_index("ix_pyq_section_pdfs_section_id", table_name="pyq_section_pdfs")
        op.drop_table("pyq_section_pdfs")
    if has_table("pyq_sections"):
        op.drop_index("ix_pyq_sections_is_active", table_name="pyq_sections")
        op.drop_index("ix_pyq_sections_category_id", table_name="pyq_sections")
        op.drop_table("pyq_sections")
    if has_table("pyq_categories"):
        op.drop_index("ix_pyq_categories_is_active", table_name="pyq_categories")
        op.drop_index("ix_pyq_categories_code", table_name="pyq_categories")
        op.drop_table("pyq_categories")
