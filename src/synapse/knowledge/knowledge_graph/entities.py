"""Entity models for the SYNAPSE knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from synapse.domain.contracts import utc_now
from synapse.domain.errors import ValidationDomainError
from synapse.domain.provenance import Provenance


@dataclass(frozen=True, slots=True)
class Entity:
    """A uniquely identified subject in the knowledge graph."""

    canonical_name: str
    entity_type: str
    provenance: Provenance

    id: str = field(default_factory=lambda: str(uuid4()))
    aliases: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for name in ("canonical_name", "entity_type", "id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationDomainError(
                    f"{name} must be a non-empty string."
                )

        if not isinstance(self.provenance, Provenance):
            raise ValidationDomainError(
                "provenance must be a Provenance instance."
            )

        if not isinstance(self.aliases, tuple):
            raise ValidationDomainError(
                "aliases must be a tuple of strings."
            )

        for alias in self.aliases:
            if not isinstance(alias, str) or not alias.strip():
                raise ValidationDomainError(
                    "Every alias must be a non-empty string."
                )

        normalized_names = [
            self.canonical_name.strip().casefold(),
            *(alias.strip().casefold() for alias in self.aliases),
        ]

        if len(normalized_names) != len(set(normalized_names)):
            raise ValidationDomainError(
                "Entity canonical name and aliases must be unique."
            )

        if not isinstance(self.created_at, datetime):
            raise ValidationDomainError("created_at must be a datetime.")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValidationDomainError(
                "created_at must be timezone-aware."
            )