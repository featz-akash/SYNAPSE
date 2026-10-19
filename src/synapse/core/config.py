
"""Centralized runtime configuration for SYNAPSE."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from synapse.persistence.database import resolve_database_url

Permission = Literal[
    "objectives:read",
    "objectives:write",
    "tasks:read",
    "tasks:write",
]


class Settings(BaseSettings):
    """Validated runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="SYNAPSE_",
        extra="ignore",
        case_sensitive=False,
    )

    env: Literal["development", "test", "production"] = "development"
    log_level: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = "INFO"

    database_url: str = Field(min_length=1)

    api_token: SecretStr | None = None
    api_permissions: Annotated[
        frozenset[Permission],
        NoDecode,
    ] = Field(default_factory=frozenset)

    model_provider: str = "mock"
    model_api_key: SecretStr | None = None
    model_name: str | None = None

    autonomy_enabled: bool = False
    require_approval_for_sensitive_actions: bool = True

    @model_validator(mode="before")
    @classmethod
    def parse_permission_string(cls, values: object) -> object:
        """Parse comma-separated permissions from configuration."""
        if not isinstance(values, dict):
            return values

        values = dict(values)
        raw = values.get("api_permissions")

        if isinstance(raw, str):
            values["api_permissions"] = frozenset(
                part.strip()
                for part in raw.split(",")
                if part.strip()
            )

        return values

    @model_validator(mode="after")
    def validate_runtime_configuration(self) -> Settings:
        """Validate the database URL and production security requirements."""
        resolve_database_url(self.database_url)

        if self.env == "production":
            if self.api_token is None:
                raise ValueError(
                    "SYNAPSE_API_TOKEN is required in production."
                )

            token = self.api_token.get_secret_value()

            if len(token) < 32:
                raise ValueError(
                    "SYNAPSE_API_TOKEN must be at least 32 characters "
                    "in production."
                )

            if not self.api_permissions:
                raise ValueError(
                    "SYNAPSE_API_PERMISSIONS must not be empty in production."
                )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached process-wide settings instance."""
    return Settings()  # type: ignore[call-arg]
