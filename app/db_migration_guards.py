"""
Idempotent checks for Alembic migrations (handles DB / revision drift).
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


def has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in insp.get_columns(table_name))


def has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table(table_name):
        return False
    return any(idx.get("name") == index_name for idx in insp.get_indexes(table_name))
