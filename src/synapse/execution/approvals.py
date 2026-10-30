
"""Thread-safe, in-memory approval tracking for SYNAPSE actions.

Approvals are bound to action IDs. This registry is process-local and
does not provide durable storage or cross-process coordination.

Revocation prevents new approval claims. It does not cancel an action
whose approval was claimed before revocation.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from collections.abc import Iterator


class ApprovalError(Exception):
    """Base exception for approval failures."""


class ApprovalRequiredError(ApprovalError):
    """Raised when an action has not been explicitly approved."""


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    """Approval metadata for one proposed action."""

    action_id: str
    approver_id: str
    approved_at: datetime


class ApprovalRegistry:
    """Thread-safe, process-local approval registry."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._approvals: dict[str, ApprovalRecord] = {}
        self._in_flight: dict[str, int] = {}

    def approve(
        self,
        *,
        action_id: str,
        approver_id: str,
        approved_at: datetime | None = None,
    ) -> ApprovalRecord:
        """Record approval for a specific action ID."""
        if not isinstance(action_id, str) or not action_id.strip():
            raise ValueError("action_id must be a nonblank string.")

        if not isinstance(approver_id, str) or not approver_id.strip():
            raise ValueError("approver_id must be a nonblank string.")

        timestamp = (
            datetime.now(UTC) if approved_at is None else approved_at
        )
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("approved_at must be timezone-aware.")

        record = ApprovalRecord(
            action_id=action_id,
            approver_id=approver_id,
            approved_at=timestamp,
        )

        with self._lock:
            self._approvals[action_id] = record

        return record

    def get(self, action_id: str) -> ApprovalRecord | None:
        """Return approval metadata, if present."""
        with self._lock:
            return self._approvals.get(action_id)

    def is_approved(self, action_id: str) -> bool:
        """Return whether an action currently has an approval."""
        with self._lock:
            return action_id in self._approvals

    def require_approved(self, action_id: str) -> ApprovalRecord:
        """Require a current approval without claiming it for execution."""
        with self._lock:
            record = self._approvals.get(action_id)

        if record is None:
            raise ApprovalRequiredError(
                f"Explicit approval required for action: {action_id}"
            )

        return record

    @contextmanager
    def hold_approval(
        self, action_id: str
    ) -> Iterator[ApprovalRecord]:
        """Atomically claim approval before a protected operation starts.

        The registry lock is not held while the operation runs. Revocation
        may proceed, but it cannot retroactively invalidate this claim.
        """
        with self._lock:
            record = self._approvals.get(action_id)
            if record is None:
                raise ApprovalRequiredError(
                    f"Explicit approval required for action: {action_id}"
                )

            self._in_flight[action_id] = (
                self._in_flight.get(action_id, 0) + 1
            )

        try:
            yield record
        finally:
            with self._lock:
                remaining = self._in_flight[action_id] - 1
                if remaining:
                    self._in_flight[action_id] = remaining
                else:
                    del self._in_flight[action_id]

    def revoke(self, action_id: str) -> bool:
        """Revoke approval for future claims."""
        with self._lock:
            return self._approvals.pop(action_id, None) is not None
