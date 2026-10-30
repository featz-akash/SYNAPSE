

"""Permission checks for proposed SYNAPSE actions.

Permission context must come from a trusted authorization boundary,
never directly from model-generated or user-controlled payload fields.
"""

from __future__ import annotations

from synapse.domain.contracts import ActionKind, ProposedAction
from synapse.security.policy_engine import PolicyContext


_REQUIRED_PERMISSION: dict[ActionKind, str] = {
    ActionKind.READ: "actions:read",
    ActionKind.WRITE: "actions:write",
    ActionKind.DELETE: "actions:delete",
    ActionKind.EXTERNAL_SIDE_EFFECT: "actions:external_side_effect",
}


class PermissionDeniedError(PermissionError):
    """Raised when the trusted principal lacks an action permission."""


class PermissionChecker:
    """Check explicit permissions without wildcards or implicit grants."""

    def required_permission(self, action: ProposedAction) -> str:
        """Return the exact permission required for an action."""
        if not isinstance(action, ProposedAction):
            raise TypeError("action must be a ProposedAction.")

        permission = _REQUIRED_PERMISSION.get(action.kind)
        if permission is None:
            raise PermissionDeniedError("Unsupported action kind.")

        return permission

    def check(
        self,
        action: ProposedAction,
        context: PolicyContext,
    ) -> None:
        """Return normally when authorized; otherwise raise."""
        if not isinstance(context, PolicyContext):
            raise TypeError("context must be a PolicyContext.")

        required = self.required_permission(action)
        if required not in context.granted_permissions:
            raise PermissionDeniedError(
                f"Missing required permission: {required}"
            )

    def is_allowed(
        self,
        action: ProposedAction,
        context: PolicyContext,
    ) -> bool:
        """Check permission without exposing exceptions to simple callers."""
        try:
            self.check(action, context)
        except PermissionDeniedError:
            return False
        return True
