"""PostgreSQL engine and session-factory configuration for SYNAPSE."""

from __future__ import annotations

import os
from collections.abc import Mapping

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENV = "SYNAPSE_DATABASE_URL"


def resolve_database_url(
    database_url: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve and validate a PostgreSQL URL without exposing credentials in errors."""
    if environ is None:
        environ = os.environ

    candidate = database_url if database_url is not None else environ.get(DATABASE_URL_ENV)
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(
            f"A database URL is required; set {DATABASE_URL_ENV} or pass database_url."
        )

    try:
        parsed = make_url(candidate)
    except (ArgumentError, TypeError, ValueError) as exc:
        raise ValueError("The configured database URL is invalid.") from exc

    if not parsed.drivername.startswith("postgresql"):
        raise ValueError("SYNAPSE requires a PostgreSQL database URL.")

    if not parsed.database or not parsed.database.strip():
        raise ValueError("The PostgreSQL URL must specify a database name.")

    if not parsed.host or not parsed.host.strip():
        raise ValueError("The PostgreSQL URL must specify a host.")

    return candidate


def create_database_engine(
    database_url: str | None = None,
    *,
    echo: bool = False,
    pool_pre_ping: bool = True,
    environ: Mapping[str, str] | None = None,
) -> Engine:
    """Create a PostgreSQL engine; connections are opened lazily by SQLAlchemy."""
    url = resolve_database_url(database_url, environ=environ)
    return create_engine(url, echo=echo, pool_pre_ping=pool_pre_ping)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions with predictable commit/expiration behavior."""
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
