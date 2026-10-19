
"""Tests for centralized SYNAPSE runtime configuration."""

import pytest
from pydantic import ValidationError

from synapse.core.config import Settings

VALID_DATABASE_URL = "postgresql+psycopg://user:pass@localhost:5432/synapse"


def test_development_defaults_are_safe() -> None:
    settings = Settings(
        database_url=VALID_DATABASE_URL,
        _env_file=None,
    )

    assert settings.env == "development"
    assert settings.api_token is None
    assert settings.api_permissions == frozenset()
    assert settings.autonomy_enabled is False
    assert settings.require_approval_for_sensitive_actions is True


def test_api_permissions_parse_from_comma_separated_string() -> None:
    settings = Settings(
        database_url=VALID_DATABASE_URL,
        api_permissions="tasks:read,tasks:write",
        _env_file=None,
    )

    assert settings.api_permissions == frozenset(
        {"tasks:read", "tasks:write"}
    )


def test_unknown_permission_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url=VALID_DATABASE_URL,
            api_permissions="admin:everything",
            _env_file=None,
        )


def test_production_requires_token() -> None:
    with pytest.raises(ValidationError, match="required in production"):
        Settings(
            env="production",
            database_url=VALID_DATABASE_URL,
            api_permissions="tasks:read",
            _env_file=None,
        )


def test_production_rejects_short_token() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(
            env="production",
            database_url=VALID_DATABASE_URL,
            api_token="short-token",
            api_permissions="tasks:read",
            _env_file=None,
        )


def test_production_requires_permissions() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        Settings(
            env="production",
            database_url=VALID_DATABASE_URL,
            api_token="x" * 32,
            _env_file=None,
        )


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url=VALID_DATABASE_URL,
            log_level="VERBOSE",
            _env_file=None,
        )


def test_non_postgresql_database_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires a PostgreSQL"):
        Settings(
            database_url="sqlite:///synapse.db",
            _env_file=None,
        )
