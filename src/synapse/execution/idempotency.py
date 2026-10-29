

"""In-memory idempotency tracking for SYNAPSE tool execution.

This module provides process-local duplicate detection. It does not
guarantee exactly-once execution across crashes or multiple processes.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar


T = TypeVar("T")


class IdempotencyError(Exception):
    """Base exception for idempotency failures."""


class IdempotencyConflictError(IdempotencyError):
    """An idempotency key was reused for a different action."""


class IdempotencyInProgressError(IdempotencyError):
    """An action with this key is already executing."""


@dataclass(frozen=True, slots=True)
class IdempotencyRecord(Generic[T]):
    key: str
    action_fingerprint: str
    result: T


class IdempotencyRegistry:
    """Track in-progress and completed action keys safely within one process."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._in_progress: dict[str, str] = {}
        self._completed: dict[str, IdempotencyRecord[object]] = {}

    def begin(self, key: str, action_fingerprint: str) -> bool:
        """Reserve a key; return False if the same action already completed."""
        self._validate(key, "key")
        self._validate(action_fingerprint, "action_fingerprint")

        with self._lock:
            completed = self._completed.get(key)
            if completed is not None:
                if completed.action_fingerprint != action_fingerprint:
                    raise IdempotencyConflictError(
                        "Idempotency key was reused for a different action."
                    )
                return False

            active = self._in_progress.get(key)
            if active is not None:
                if active != action_fingerprint:
                    raise IdempotencyConflictError(
                        "In-progress key belongs to a different action."
                    )
                raise IdempotencyInProgressError(
                    "An action with this key is already in progress."
                )

            self._in_progress[key] = action_fingerprint
            return True

    def complete(self, key: str, result: object) -> None:
        """Store a result and release its in-progress reservation."""
        with self._lock:
            fingerprint = self._in_progress.get(key)
            if fingerprint is None:
                raise IdempotencyError(
                    "Cannot complete a key that is not in progress."
                )

            self._completed[key] = IdempotencyRecord(
                key=key,
                action_fingerprint=fingerprint,
                result=result,
            )
            del self._in_progress[key]

    def fail(self, key: str) -> None:
        """Release a failed reservation so a retry can be attempted."""
        with self._lock:
            self._in_progress.pop(key, None)

    def get_completed(
        self,
        key: str,
        action_fingerprint: str,
    ) -> IdempotencyRecord[object] | None:
        """Retrieve a cached result only when its fingerprint matches."""
        self._validate(key, "key")
        self._validate(action_fingerprint, "action_fingerprint")

        with self._lock:
            record = self._completed.get(key)
            if record is None:
                return None
            if record.action_fingerprint != action_fingerprint:
                raise IdempotencyConflictError(
                    "Idempotency key was reused for a different action."
                )
            return record

    @staticmethod
    def _validate(value: str, field_name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a nonblank string.")
