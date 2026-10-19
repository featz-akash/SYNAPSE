"""SQLAlchemy declarative base for SYNAPSE persistence models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base metadata registry for ORM models and Alembic migrations."""
