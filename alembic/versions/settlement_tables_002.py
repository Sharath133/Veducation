"""duel settlement tables and user payout fund account

Revision ID: settlement_002
Revises: add_is_admin_001
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.db_migration_guards import has_column, has_index, has_table

revision = "settlement_002"
down_revision = "add_is_admin_001"
branch_labels = None
depends_on = None


def upgrade():
    if not has_table("duel_settlements"):
        op.create_table(
            "duel_settlements",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("duel_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("rankings_finalized_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("records_written_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["duel_id"], ["daily_duels.id"], ondelete="CASCADE"),
        )
    if has_table("duel_settlements"):
        if not has_index("duel_settlements", "ix_duel_settlements_duel_id"):
            op.create_index("ix_duel_settlements_duel_id", "duel_settlements", ["duel_id"], unique=True)
        if not has_index("duel_settlements", "ix_duel_settlements_status"):
            op.create_index("ix_duel_settlements_status", "duel_settlements", ["status"])

    if not has_table("settlement_payouts"):
        op.create_table(
            "settlement_payouts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("settlement_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("amount_rupees", sa.Numeric(12, 2), nullable=False),
            sa.Column("reference_id", sa.String(length=128), nullable=False),
            sa.Column("razorpay_fund_account_id", sa.String(length=255), nullable=True),
            sa.Column("razorpay_payout_id", sa.String(length=255), nullable=True),
            sa.Column("payout_status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["settlement_id"], ["duel_settlements.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["attempt_id"], ["user_attempts.id"]),
            sa.UniqueConstraint("reference_id", name="uq_settlement_payout_reference_id"),
        )
    if has_table("settlement_payouts"):
        for idx_name, cols, unique in (
            ("ix_settlement_payouts_settlement_id", ["settlement_id"], False),
            ("ix_settlement_payouts_user_id", ["user_id"], False),
            ("ix_settlement_payouts_attempt_id", ["attempt_id"], False),
            ("ix_settlement_payouts_payout_status", ["payout_status"], False),
        ):
            if not has_index("settlement_payouts", idx_name):
                op.create_index(idx_name, "settlement_payouts", cols, unique=unique)

    if not has_column("users", "razorpay_fund_account_id"):
        op.add_column("users", sa.Column("razorpay_fund_account_id", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("users", "razorpay_fund_account_id")
    op.drop_index("ix_settlement_payouts_payout_status", table_name="settlement_payouts")
    op.drop_index("ix_settlement_payouts_attempt_id", table_name="settlement_payouts")
    op.drop_index("ix_settlement_payouts_user_id", table_name="settlement_payouts")
    op.drop_index("ix_settlement_payouts_settlement_id", table_name="settlement_payouts")
    op.drop_table("settlement_payouts")
    op.drop_index("ix_duel_settlements_status", table_name="duel_settlements")
    op.drop_index("ix_duel_settlements_duel_id", table_name="duel_settlements")
    op.drop_table("duel_settlements")
