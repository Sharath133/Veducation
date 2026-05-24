"""baseline current model schema

Revision ID: initial_schema_000
Revises:
Create Date: 2026-05-24

This project originally relied on SQLAlchemy ``create_all`` for the base
schema and kept Alembic revisions only for later incremental changes. Docker
runs Alembic before the FastAPI startup hook, so a fresh database needs this
baseline revision before the incremental migrations can run.
"""
from alembic import op

from app.database import Base


revision = "initial_schema_000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
