"""Run evidence assessment before bounded inference; never mutate graph state."""
from __future__ import annotations

from synapse.domain.errors import ValidationDomainError
from synapse.knowledge.knowledge_graph.engine import KnowledgeGraph
from synapse.reasoning.assessment.engine import EvidenceAssessmentEngine
from synapse.reasoning.assessment.models import AssessmentStatus
from synapse.reasoning.assessment.verifier import EvidenceAssessmentVerifier
from synapse.reasoning.inference.engine import BoundedInferenceEngine
from synapse.reasoning.inference.models import InferenceRule
from synapse.reasoning.inference.verifier import DerivationVerifier
from synapse.reasoning.pipeline.models import ReasoningPipelineResult

class ReasoningPipeline:
    """Compose graph-backed assessment and explicit-rule inference.

    Only claims assessed as SUPPORTED are admitted as inference seeds. Conflicted,
    contradicted, and inconclusive claims are excluded from this conservative path.
    This is a policy choice for this pipeline, not a universal truth calculus.
    """
    def __init__(self, graph: KnowledgeGraph) -> None:
        if not isinstance(graph, KnowledgeGraph):
            raise ValidationDomainError("graph must be a KnowledgeGraph.")
        self._graph = graph
        self._assessment = EvidenceAssessmentEngine(graph)
        self._assessment_verifier = EvidenceAssessmentVerifier(graph)
        self._inference = BoundedInferenceEngine()
        self._derivation_verifier = DerivationVerifier()

    def run(
        self,
        claim_ids: tuple[str, ...],
        rules: tuple[InferenceRule, ...],
        *,
        max_depth: int = 3,
    ) -> ReasoningPipelineResult:
        if not isinstance(claim_ids, tuple) or not claim_ids:
            raise ValidationDomainError("claim_ids must be a non-empty tuple.")
        if any(not isinstance(cid, str) or not cid.strip() for cid in claim_ids):
            raise ValidationDomainError("claim_ids must contain non-empty strings.")
        if len(set(claim_ids)) != len(claim_ids):
            raise ValidationDomainError("claim_ids must be unique.")

        assessments = tuple(self._assessment.assess(cid) for cid in claim_ids)
        assessment_ok = all(self._assessment_verifier.verify(item) for item in assessments)
        eligible = tuple(
            item.claim_id for item in assessments
            if item.status is AssessmentStatus.SUPPORTED
        )
        inference_result = self._inference.infer(eligible, rules, max_depth=max_depth)
        derivation_ok = self._derivation_verifier.verify(inference_result, rules)
        return ReasoningPipelineResult(
            assessments=assessments,
            inference=inference_result,
            eligible_seed_claim_ids=eligible,
            assessment_verification_passed=assessment_ok,
            derivation_verification_passed=derivation_ok,
        )
