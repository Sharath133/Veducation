"""add_is_admin_to_users

Revision ID: add_is_admin_001
Revises: 
Create Date: 2025-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.db_migration_guards import has_column, has_index


# revision identifiers, used by Alembic.
revision = 'add_is_admin_001'
down_revision = "initial_schema_000"
branch_labels = None
depends_on = None


def upgrade():
    if not has_column("users", "is_admin"):
        op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false'))
    if has_column("users", "is_admin") and not has_index("users", "ix_users_is_admin"):
        op.create_index('ix_users_is_admin', 'users', ['is_admin'])


def downgrade():
    # Remove index
    op.drop_index('ix_users_is_admin', table_name='users')
    # Remove column
    op.drop_column('users', 'is_admin')
