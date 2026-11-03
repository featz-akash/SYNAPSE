"""Fail-closed reasoning eligibility gate for controller policy evaluation.

Reasoning eligibility is an additional prerequisite, never a replacement for
permission checks, explicit approval, or downstream execution safeguards.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from synapse.cognition.controller.policy_gate import (
    ControllerPolicyEvaluation,
    ControllerPolicyGate,
)
from synapse.domain.contracts import ProposedAction
from synapse.reasoning.assessment.models import AssessmentStatus
from synapse.reasoning.pipeline.models import ReasoningPipelineResult
from synapse.security.audit import AuditEvent
from synapse.security.policy_engine import PolicyContext, PolicyDecision


@dataclass(frozen=True, slots=True)
class ReasoningEligibility:
    """Auditable result of checking reasoning output for controller use."""

    eligible: bool
    reason_code: str
    message: str
    claim_ids: tuple[str, ...]


class ControllerReasoningGate:
    """Require verified supported claims before normal action-policy evaluation."""

    def __init__(
        self,
        policy_gate: ControllerPolicyGate | None = None,
    ) -> None:
        self._policy_gate = policy_gate or ControllerPolicyGate()

    @staticmethod
    def assess_eligibility(
        reasoning: ReasoningPipelineResult,
    ) -> ReasoningEligibility:
        """Fail closed if verification fails or any assessment is not supported."""
        if not isinstance(reasoning, ReasoningPipelineResult):
            return ReasoningEligibility(
                eligible=False,
                reason_code="reasoning_result_invalid",
                message="A valid reasoning pipeline result is required.",
                claim_ids=(),
            )

        claim_ids = tuple(item.claim_id for item in reasoning.assessments)
        if not reasoning.verification_passed:
            return ReasoningEligibility(
                eligible=False,
                reason_code="reasoning_verification_failed",
                message="Reasoning verification did not pass.",
                claim_ids=claim_ids,
            )

        if not reasoning.assessments:
            return ReasoningEligibility(
                eligible=False,
                reason_code="reasoning_assessment_missing",
                message="At least one evidence assessment is required.",
                claim_ids=(),
            )

        ineligible = tuple(
            item for item in reasoning.assessments
            if item.status is not AssessmentStatus.SUPPORTED
        )
        if ineligible:
            status_names = ", ".join(
                f"{item.claim_id}:{item.status.value}" for item in ineligible
            )
            return ReasoningEligibility(
                eligible=False,
                reason_code="reasoning_evidence_not_supported",
                message=(
                    "Controller reasoning requires every supplied claim to be "
                    f"supported; ineligible assessments: {status_names}."
                ),
                claim_ids=claim_ids,
            )

        # Require all assessed claims to be included in the pipeline's admitted
        # seed set, so a malformed/inconsistent result cannot pass this boundary.
        if not set(claim_ids).issubset(set(reasoning.eligible_seed_claim_ids)):
            return ReasoningEligibility(
                eligible=False,
                reason_code="reasoning_seed_mismatch",
                message="Assessment claims and eligible inference seeds disagree.",
                claim_ids=claim_ids,
            )

        return ReasoningEligibility(
            eligible=True,
            reason_code="reasoning_supported",
            message="Reasoning verification passed for supported evidence.",
            claim_ids=claim_ids,
        )

    def evaluate(
        self,
        action: ProposedAction,
        context: PolicyContext,
        reasoning: ReasoningPipelineResult,
        *,
        correlation_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> ControllerPolicyEvaluation:
        """Evaluate reasoning first, then existing policy only if eligible.

        The returned event remains an action policy decision event. No action is
        executed here. An ineligible reasoning result produces a denial.
        """
        eligibility = self.assess_eligibility(reasoning)
        if eligibility.eligible:
            return self._policy_gate.evaluate(
                action,
                context,
                correlation_id=correlation_id,
                occurred_at=occurred_at,
            )

        decision = PolicyDecision(
            allowed=False,
            reason_code=eligibility.reason_code,
            message=eligibility.message,
            action_id=action.id,
            actor_id=context.actor_id,
        )
        event = AuditEvent.from_policy_decision(
            decision,
            objective_id=action.objective_id,
            task_id=action.task_id,
            occurred_at=occurred_at,
            correlation_id=correlation_id,
        )
        return ControllerPolicyEvaluation(decision=decision, audit_event=event)
