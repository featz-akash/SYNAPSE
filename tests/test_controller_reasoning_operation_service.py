"""Integration tests for the reasoning-required operation path."""

from unittest.mock import Mock

from synapse.cognition.controller.operation_service import ControllerOperationService
from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.reasoning.assessment.models import AssessmentStatus, EvidenceAssessment
from synapse.reasoning.inference.models import InferenceResult
from synapse.reasoning.pipeline.models import ReasoningPipelineResult
from synapse.security.audit import AuditOutcome
from synapse.security.policy_engine import PolicyContext


def _action() -> ProposedAction:
    objective = Objective(title="Check claim", success_criteria=("Evidence checked",))
    task = Task(objective_id=objective.id, title="Inspect claim")
    return ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="inspect",
        kind=ActionKind.READ,
    )


def _reasoning(status: AssessmentStatus, verified: bool = True) -> ReasoningPipelineResult:
    claim_id = "claim-1"
    assessment = EvidenceAssessment(
        claim_id=claim_id,
        status=status,
        supporting_link_ids=("link-1",) if status is AssessmentStatus.SUPPORTED else (),
        contradicting_link_ids=(),
        contextual_link_ids=(),
    )
    seeds = (claim_id,) if status is AssessmentStatus.SUPPORTED else ()
    return ReasoningPipelineResult(
        assessments=(assessment,),
        inference=InferenceResult(input_claim_ids=seeds, derivations=(), max_depth=2),
        eligible_seed_claim_ids=seeds,
        assessment_verification_passed=verified,
        derivation_verification_passed=verified,
    )


def _context() -> PolicyContext:
    return PolicyContext(actor_id="controller-1", granted_permissions=frozenset({"actions:read"}))


def test_reasoning_and_policy_allow_then_operation_runs() -> None:
    operation = Mock(return_value="ok")
    result = ControllerOperationService().execute_if_reasoning_allowed(
        _action(), _context(), _reasoning(AssessmentStatus.SUPPORTED), operation
    )
    assert result.executed is True
    assert result.result == "ok"
    assert result.evaluation.decision.allowed is True
    assert result.evaluation.audit_event.outcome is AuditOutcome.ALLOWED
    operation.assert_called_once_with()


def test_unsupported_reasoning_blocks_operation() -> None:
    operation = Mock(return_value="must-not-run")
    result = ControllerOperationService().execute_if_reasoning_allowed(
        _action(), _context(), _reasoning(AssessmentStatus.CONFLICTED), operation
    )
    assert result.executed is False
    assert result.evaluation.decision.reason_code == "reasoning_evidence_not_supported"
    assert result.evaluation.audit_event.outcome is AuditOutcome.DENIED
    operation.assert_not_called()


def test_policy_permission_still_blocks_supported_reasoning() -> None:
    operation = Mock(return_value="must-not-run")
    context = PolicyContext(actor_id="controller-1", granted_permissions=frozenset())
    result = ControllerOperationService().execute_if_reasoning_allowed(
        _action(), context, _reasoning(AssessmentStatus.SUPPORTED), operation
    )
    assert result.executed is False
    assert result.evaluation.decision.reason_code == "permission_missing"
    operation.assert_not_called()


def test_failed_verification_blocks_operation() -> None:
    operation = Mock(return_value="must-not-run")
    result = ControllerOperationService().execute_if_reasoning_allowed(
        _action(), _context(), _reasoning(AssessmentStatus.SUPPORTED, verified=False), operation
    )
    assert result.executed is False
    assert result.evaluation.decision.reason_code == "reasoning_verification_failed"
    operation.assert_not_called()
