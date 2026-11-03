"""Tests for reasoning eligibility as an additive controller gate."""

from synapse.cognition.controller.reasoning_gate import ControllerReasoningGate
from synapse.reasoning.assessment.models import AssessmentStatus, EvidenceAssessment
from synapse.reasoning.inference.models import InferenceResult
from synapse.reasoning.pipeline.models import ReasoningPipelineResult


def _assessment(claim_id: str, status: AssessmentStatus) -> EvidenceAssessment:
    return EvidenceAssessment(
        claim_id=claim_id,
        status=status,
        supporting_link_ids=("support-1",) if status is AssessmentStatus.SUPPORTED else (),
        contradicting_link_ids=(),
        contextual_link_ids=(),
    )


def _result(
    statuses: tuple[AssessmentStatus, ...],
    *,
    verified: bool = True,
) -> ReasoningPipelineResult:
    assessments = tuple(
        _assessment(f"claim-{index}", status)
        for index, status in enumerate(statuses)
    )
    eligible = tuple(
        item.claim_id for item in assessments
        if item.status is AssessmentStatus.SUPPORTED
    )
    inference = InferenceResult(
        input_claim_ids=eligible,
        derivations=(),
        max_depth=2,
    )
    return ReasoningPipelineResult(
        assessments=assessments,
        inference=inference,
        eligible_seed_claim_ids=eligible,
        assessment_verification_passed=verified,
        derivation_verification_passed=verified,
    )


def test_supported_verified_assessment_is_eligible() -> None:
    result = ControllerReasoningGate.assess_eligibility(
        _result((AssessmentStatus.SUPPORTED,))
    )
    assert result.eligible is True
    assert result.reason_code == "reasoning_supported"


def test_contradicted_conflicted_and_inconclusive_are_ineligible() -> None:
    for status in (
        AssessmentStatus.CONTRADICTED,
        AssessmentStatus.CONFLICTED,
        AssessmentStatus.INCONCLUSIVE,
    ):
        result = ControllerReasoningGate.assess_eligibility(_result((status,)))
        assert result.eligible is False
        assert result.reason_code == "reasoning_evidence_not_supported"


def test_verification_failure_fails_closed() -> None:
    result = ControllerReasoningGate.assess_eligibility(
        _result((AssessmentStatus.SUPPORTED,), verified=False)
    )
    assert result.eligible is False
    assert result.reason_code == "reasoning_verification_failed"


def test_empty_assessments_fail_closed() -> None:
    result = ControllerReasoningGate.assess_eligibility(_result(()))
    assert result.eligible is False
    assert result.reason_code == "reasoning_assessment_missing"
