"""Claim representation for SYNAPSE knowledge processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from synapse.domain.contracts import utc_now
from synapse.domain.errors import ValidationDomainError
from synapse.domain.provenance import Provenance


@dataclass(frozen=True, slots=True)
class Claim:
    """
    An assertion that can be evaluated using evidence and reasoning.

    A Claim is not an established fact. Its assessment belongs
    to the belief and verification layers.
    """

    proposition: str
    provenance: Provenance

    id: str = field(default_factory=lambda: str(uuid4()))
    normalized_text: str | None = None
    scope: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not isinstance(self.proposition, str) or not self.proposition.strip():
            raise ValidationDomainError(
                "proposition must be a non-empty string."
            )

        if not isinstance(self.id, str) or not self.id.strip():
            raise ValidationDomainError(
                "id must be a non-empty string."
            )

        if not isinstance(self.provenance, Provenance):
            raise ValidationDomainError(
                "provenance must be a Provenance instance."
            )

        if self.normalized_text is not None:
            if (
                not isinstance(self.normalized_text, str)
                or not self.normalized_text.strip()
            ):
                raise ValidationDomainError(
                    "normalized_text must be non-empty when provided."
                )

        if self.scope is not None:
            if not isinstance(self.scope, str) or not self.scope.strip():
                raise ValidationDomainError(
                    "scope must be non-empty when provided."
                )

        if not isinstance(self.created_at, datetime):
            raise ValidationDomainError(
                "created_at must be a datetime."
            )

        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise ValidationDomainError(
                "created_at must be timezone-aware."
            )