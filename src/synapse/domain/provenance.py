"""Immutable provenance contracts for SYNAPSE domain records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from synapse.domain.contracts import utc_now
from synapse.domain.errors import ValidationDomainError


def _require_nonblank(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationDomainError(
            f"{field_name} must be a non-empty string.",
            details={"field": field_name},
        )


def _require_aware_datetime(value: object, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ValidationDomainError(
            f"{field_name} must be a datetime."
        )

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationDomainError(
            f"{field_name} must be timezone-aware."
        )


def _require_string_tuple(value: object, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise ValidationDomainError(
            f"{field_name} must be a tuple of strings."
        )

    for index, item in enumerate(value):
        _require_nonblank(item, f"{field_name}[{index}]")

    if len(value) != len(set(value)):
        raise ValidationDomainError(
            f"{field_name} must contain unique values."
        )


@dataclass(frozen=True, slots=True)
class Provenance:
    """
    Describes the origin and acquisition context of a domain record.

    Provenance records origin, not truth or reliability.
    """

    source: str
    method: str

    id: str = field(default_factory=lambda: __import__("uuid").uuid4().__str__())
    actor: str | None = None
    source_reference: str | None = None
    recorded_at: datetime = field(default_factory=utc_now)
    parent_record_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_nonblank(self.source, "source")
        _require_nonblank(self.method, "method")
        _require_nonblank(self.id, "id")

        if self.actor is not None:
            _require_nonblank(self.actor, "actor")

        if self.source_reference is not None:
            _require_nonblank(self.source_reference, "source_reference")

        _require_aware_datetime(self.recorded_at, "recorded_at")
        _require_string_tuple(self.parent_record_ids, "parent_record_ids")