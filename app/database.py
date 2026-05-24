"""
Database Configuration
"""
import logging
import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

logger = logging.getLogger(__name__)

# Create database engine (SQLite uses a single connection pool for in-memory tests)
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Register all models on Base.metadata (for create_all and Alembic)
import app.models  # noqa: E402, F401


def ensure_postgres_database_exists(database_url: str) -> None:
    """
    If DATABASE_URL targets PostgreSQL and the database is missing, create it
    (requires CONNECT on the maintenance DB and CREATEDB / superuser — typical for local dev).
    No-op for SQLite. Skips if the name is not a simple identifier.
    """
    if database_url.startswith("sqlite"):
        return

    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or not url.database:
        return

    db_name = url.database
    if not re.fullmatch(r"[A-Za-z0-9_]+", db_name):
        logger.warning("Skipping auto-create: database name must be alphanumeric or underscore")
        return

    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :d"),
                {"d": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info("Created PostgreSQL database %r", db_name)
    finally:
        admin_engine.dispose()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

