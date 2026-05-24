#!/bin/sh
set -e
cd /app
# Keep Docker DB schema in sync with models (idempotent)
python -m alembic upgrade head
exec "$@"
