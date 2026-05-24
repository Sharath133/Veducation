"""Merge four parallel migration heads into a single lineage.

Revision ID: merge_four_heads_003
Revises: loyalty_free_entry_002, admin_msg_pyq_pdf_001, settlement_002, support_fb_002
Create Date: 2026-04-19

After this revision exists, ``alembic upgrade head`` resolves to one head.
No-op upgrade: schema changes live on the merged branches.
"""

revision = "merge_four_heads_003"
down_revision = (
    "loyalty_free_entry_002",
    "admin_msg_pyq_pdf_001",
    "settlement_002",
    "support_fb_002",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
