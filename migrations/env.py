"""Alembic environment for SYNAPSE."""

from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import dotenv_values
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from synapse.persistence import models  # noqa: F401
from synapse.persistence.models import Base  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

project_root = Path(__file__).resolve().parents[1]
env_file = project_root / ".env"
file_values = dotenv_values(env_file) if env_file.exists() else {}
database_url = os.environ.get("SYNAPSE_DATABASE_URL") or file_values.get(
    "SYNAPSE_DATABASE_URL"
)
if not database_url:
    raise RuntimeError(
        "SYNAPSE_DATABASE_URL must be set in the environment or project .env file."
    )

parsed_url = make_url(database_url)
if not parsed_url.drivername.startswith("postgresql"):
    raise RuntimeError("SYNAPSE migrations require a PostgreSQL URL.")
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
