"""Evidence links connecting artifacts to assessable claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from synapse.domain.contracts import utc_now
from synapse.domain.errors import ValidationDomainError
from synapse.domain.provenance import Provenance


class EvidenceRole(StrEnum):
    """How an evidence artifact relates to a claim."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXTUAL = "contextual"


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    """An auditable association between a claim and an evidence artifact."""

    claim_id: str
    artifact_id: str
    role: EvidenceRole
    provenance: Provenance

    id: str = field(default_factory=lambda: str(uuid4()))
    linked_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for name in ("claim_id", "artifact_id", "id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationDomainError(
                    f"{name} must be a non-empty string."
                )

        if not isinstance(self.role, EvidenceRole):
            raise ValidationDomainError(
                "role must be an EvidenceRole."
            )

        if not isinstance(self.provenance, Provenance):
            raise ValidationDomainError(
                "provenance must be a Provenance instance."
            )

        if not isinstance(self.linked_at, datetime):
            raise ValidationDomainError("linked_at must be a datetime.")

        if self.linked_at.tzinfo is None or self.linked_at.utcoffset() is None:
            raise ValidationDomainError(
                "linked_at must be timezone-aware."
            )