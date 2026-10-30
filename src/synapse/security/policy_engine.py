"""Fail-closed policy evaluation for proposed SYNAPSE actions.

This module is deliberately pure: it neither executes tools nor accesses storage.
A policy decision is an authorization input, not proof that execution is safe or
that a later state transition will succeed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from synapse.domain.contracts import ActionKind, ProposedAction
from synapse.domain.errors import ValidationDomainError

POLICY_VERSION: Final[str] = "synapse-action-policy-v1"

_REQUIRED_PERMISSION: Final[dict[ActionKind, str]] = {
    ActionKind.READ: "actions:read",
    ActionKind.WRITE: "actions:write",
    ActionKind.DELETE: "actions:delete",
    ActionKind.EXTERNAL_SIDE_EFFECT: "actions:external_side_effect",
}


@dataclass(frozen=True, slots=True)
class PolicyContext:
    """Trusted authorization facts supplied by the caller's auth boundary.

    Do not build this context directly from an untrusted model/planner payload.
    Permissions must come from the authenticated principal's trusted identity
    provider or API authorization layer.
    """

    actor_id: str
    granted_permissions: frozenset[str]
    approval_granted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise ValidationDomainError("actor_id must be a nonblank string.")
        if not isinstance(self.granted_permissions, frozenset):
            raise ValidationDomainError("granted_permissions must be a frozenset.")
        for permission in self.granted_permissions:
            if not isinstance(permission, str) or not permission.strip():
                raise ValidationDomainError("Permissions must be nonblank strings.")
        if not isinstance(self.approval_granted, bool):
            raise ValidationDomainError("approval_granted must be a boolean.")


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Deterministic policy result; it never performs the proposed action."""

    allowed: bool
    reason_code: str
    message: str
    action_id: str
    actor_id: str
    policy_version: str = POLICY_VERSION


class ActionPolicyEngine:
    """Evaluate action permissions using explicit, fail-closed rules."""

    def evaluate(
        self,
        action: ProposedAction,
        context: PolicyContext,
    ) -> PolicyDecision:
        """Return an allow/deny decision without mutating inputs or side effects."""
        if not isinstance(action, ProposedAction):
            raise ValidationDomainError("action must be a ProposedAction.")
        if not isinstance(context, PolicyContext):
            raise ValidationDomainError("context must be a PolicyContext.")

        required = _REQUIRED_PERMISSION.get(action.kind)
        if required is None:
            return self._deny(
                action, context, "unknown_action_kind", "The action kind is not supported."
            )
        if required not in context.granted_permissions:
            return self._deny(
                action,
                context,
                "permission_missing",
                f"The principal lacks the required permission: {required}.",
            )
        if action.kind is ActionKind.EXTERNAL_SIDE_EFFECT and not context.approval_granted:
            return self._deny(
                action,
                context,
                "approval_required",
                "External side effects require explicit approval.",
            )

        return PolicyDecision(
            allowed=True,
            reason_code="policy_allowed",
            message="The proposed action satisfies the configured policy checks.",
            action_id=action.id,
            actor_id=context.actor_id,
        )

    @staticmethod
    def _deny(
        action: ProposedAction,
        context: PolicyContext,
        reason_code: str,
        message: str,
    ) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            reason_code=reason_code,
            message=message,
            action_id=action.id,
            actor_id=context.actor_id,
        )
