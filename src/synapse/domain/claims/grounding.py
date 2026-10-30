"""Claim-to-entity grounding domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from synapse.domain.provenance import Provenance


class ClaimEntityRole(StrEnum):
    """Semantic role played by an entity in a claim."""

    SUBJECT = "subject"
    OBJECT = "object"
    CONTEXT = "context"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ClaimEntityGrounding:
    """
    Connect an entity to a claim and record its role.

    Character offsets, when supplied, use zero-based, half-open indexing
    into Claim.proposition: [start_char, end_char).
    """

    claim_id: str
    entity_id: str
    mention_text: str
    role: ClaimEntityRole
    provenance: Provenance
    id: str = field(default_factory=lambda: str(uuid4()))
    start_char: int | None = None
    end_char: int | None = None
    grounded_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        for name in ("claim_id", "entity_id", "mention_text", "id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")

        if not isinstance(self.role, ClaimEntityRole):
            raise ValueError("role must be a ClaimEntityRole.")

        if not isinstance(self.provenance, Provenance):
            raise ValueError("provenance must be a Provenance.")

        if (self.start_char is None) != (self.end_char is None):
            raise ValueError(
                "start_char and end_char must either both be set or both be None."
            )

        if self.start_char is not None and self.end_char is not None:
            if (
                isinstance(self.start_char, bool)
                or isinstance(self.end_char, bool)
                or not isinstance(self.start_char, int)
                or not isinstance(self.end_char, int)
                or self.start_char < 0
                or self.end_char <= self.start_char
            ):
                raise ValueError("Character span must be a valid non-empty range.")

            if self.end_char - self.start_char != len(self.mention_text):
                raise ValueError(
                    "Character span length must match mention_text length."
                )

        if (
            not isinstance(self.grounded_at, datetime)
            or self.grounded_at.tzinfo is None
            or self.grounded_at.utcoffset() is None
        ):
            raise ValueError("grounded_at must be timezone-aware.")