"""Directed relationship models for the SYNAPSE knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from synapse.domain.contracts import utc_now
from synapse.domain.errors import ValidationDomainError
from synapse.domain.provenance import Provenance


@dataclass(frozen=True, slots=True)
class Relationship:
    """A typed, directed connection between two entities."""

    source_entity_id: str
    relationship_type: str
    target_entity_id: str
    provenance: Provenance

    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for name in (
            "source_entity_id",
            "relationship_type",
            "target_entity_id",
            "id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationDomainError(
                    f"{name} must be a non-empty string."
                )

        if not isinstance(self.provenance, Provenance):
            raise ValidationDomainError(
                "provenance must be a Provenance instance."
            )

        if not isinstance(self.created_at, datetime):
            raise ValidationDomainError("created_at must be a datetime.")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValidationDomainError(
                "created_at must be timezone-aware."
            )