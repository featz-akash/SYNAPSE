"""Typed, dependency-light domain contracts for the first SYNAPSE milestone.

These dataclasses validate domain-level invariants. External/model payloads must
be validated before they are converted into these trusted domain objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from uuid import uuid4

from synapse.domain.errors import ValidationDomainError


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


def _require_nonblank(value: object, field_name: str) -> None:
    """Require a nonblank string without coercing other types."""
    if not isinstance(value, str):
        raise ValidationDomainError(
            f"{field_name} must be a string.",
            details={"field": field_name, "received_type": type(value).__name__},
        )
    if not value.strip():
        raise ValidationDomainError(
            f"{field_name} must not be blank.",
            details={"field": field_name},
        )


def _require_aware(value: object, field_name: str) -> None:
    """Require a timezone-aware datetime."""
    if not isinstance(value, datetime):
        raise ValidationDomainError(
            f"{field_name} must be a datetime.",
            details={"field": field_name, "received_type": type(value).__name__},
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationDomainError(
            f"{field_name} must be timezone-aware.",
            details={"field": field_name},
        )


def _require_revision(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationDomainError("revision must be a non-negative integer.")


def _require_string_tuple(value: object, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise ValidationDomainError(
            f"{field_name} must be a tuple of strings.",
            details={"field": field_name},
        )
    for index, item in enumerate(value):
        _require_nonblank(item, f"{field_name}[{index}]")


class ActionKind(StrEnum):
    """Initial action categories; policy semantics are implemented separately."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


@dataclass(slots=True)
class Objective:
    """A user-defined goal with explicit success criteria and revision tracking."""

    title: str
    success_criteria: tuple[str, ...]
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    created_at: datetime = field(default_factory=utc_now)
    revision: int = 0

    def __post_init__(self) -> None:
        _require_nonblank(self.title, "title")
        _require_nonblank(self.id, "id")
        _require_nonblank(self.description, "description") if self.description else None
        _require_string_tuple(self.success_criteria, "success_criteria")
        if not self.success_criteria:
            raise ValidationDomainError("At least one success criterion is required.")
        _require_aware(self.created_at, "created_at")
        _require_revision(self.revision)


@dataclass(slots=True)
class Task:
    """A unit of work belonging to an objective."""

    objective_id: str
    title: str
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    dependencies: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utc_now)
    revision: int = 0

    def __post_init__(self) -> None:
        _require_nonblank(self.objective_id, "objective_id")
        _require_nonblank(self.title, "title")
        _require_nonblank(self.id, "id")
        if self.description:
            _require_nonblank(self.description, "description")
        _require_string_tuple(self.dependencies, "dependencies")
        if self.id in self.dependencies:
            raise ValidationDomainError("A task cannot depend on itself.")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValidationDomainError("Task dependencies must be unique.")
        _require_aware(self.created_at, "created_at")
        _require_revision(self.revision)


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    """Provenance-bearing evidence reference; the hash does not prove truth."""

    source: str
    content_sha256: str
    id: str = field(default_factory=lambda: str(uuid4()))
    media_type: str = "text/plain"
    storage_reference: str = ""
    captured_at: datetime = field(default_factory=utc_now)
    source_version: str | None = None
    related_artifact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_nonblank(self.source, "source")
        _require_nonblank(self.id, "id")
        _require_nonblank(self.media_type, "media_type")
        if self.storage_reference:
            _require_nonblank(self.storage_reference, "storage_reference")
        if self.source_version is not None:
            _require_nonblank(self.source_version, "source_version")
        _require_string_tuple(self.related_artifact_ids, "related_artifact_ids")
        if len(set(self.related_artifact_ids)) != len(self.related_artifact_ids):
            raise ValidationDomainError("related_artifact_ids must be unique.")
        if not isinstance(self.content_sha256, str) or len(self.content_sha256) != 64:
            raise ValidationDomainError(
                "content_sha256 must be a 64-character SHA-256 hex digest."
            )
        try:
            int(self.content_sha256, 16)
        except ValueError as exc:
            raise ValidationDomainError(
                "content_sha256 must be hexadecimal."
            ) from exc
        _require_aware(self.captured_at, "captured_at")

    @staticmethod
    def hash_content(content: bytes) -> str:
        """Compute a SHA-256 digest for bytes already obtained from a source."""
        if not isinstance(content, bytes):
            raise ValidationDomainError("content must be bytes.")
        return sha256(content).hexdigest()


@dataclass(frozen=True, slots=True)
class ProposedAction:
    """Untrusted proposal awaiting independent policy evaluation and authorization."""

    objective_id: str
    task_id: str
    tool_name: str
    kind: ActionKind
    parameters: tuple[tuple[str, str], ...] = ()
    id: str = field(default_factory=lambda: str(uuid4()))
    proposed_by: str = "planner"
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for name in ("objective_id", "task_id", "tool_name", "id", "proposed_by"):
            _require_nonblank(getattr(self, name), name)
        if not isinstance(self.kind, ActionKind):
            raise ValidationDomainError("kind must be an ActionKind.")
        _require_aware(self.created_at, "created_at")
        if not isinstance(self.parameters, tuple):
            raise ValidationDomainError(
                "parameters must be a tuple of (string, string) pairs."
            )
        keys: list[str] = []
        for index, pair in enumerate(self.parameters):
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValidationDomainError(
                    "Each action parameter must be a (name, value) tuple.",
                    details={"index": index},
                )
            key, value = pair
            _require_nonblank(key, f"parameters[{index}].name")
            if not isinstance(value, str):
                raise ValidationDomainError(
                    "Action parameter values must be strings.",
                    details={"index": index, "received_type": type(value).__name__},
                )
            keys.append(key)
        if len(keys) != len(set(keys)):
            raise ValidationDomainError("Action parameter names must be unique.")
