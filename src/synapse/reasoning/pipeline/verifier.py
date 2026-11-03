"""Independent validation of a composed reasoning pipeline result."""
from __future__ import annotations
from synapse.domain.errors import ValidationDomainError
from synapse.knowledge.knowledge_graph.engine import KnowledgeGraph
from synapse.reasoning.assessment.models import AssessmentStatus
from synapse.reasoning.assessment.verifier import EvidenceAssessmentVerifier
from synapse.reasoning.inference.models import InferenceRule
from synapse.reasoning.inference.verifier import DerivationVerifier
from synapse.reasoning.pipeline.models import ReasoningPipelineResult

class ReasoningPipelineVerifier:
    def __init__(self, graph: KnowledgeGraph) -> None:
        if not isinstance(graph, KnowledgeGraph):
            raise ValidationDomainError("graph must be a KnowledgeGraph.")
        self._assessment_verifier = EvidenceAssessmentVerifier(graph)
        self._derivation_verifier = DerivationVerifier()

    def verify(self, result: ReasoningPipelineResult, rules: tuple[InferenceRule, ...]) -> bool:
        if not isinstance(result, ReasoningPipelineResult):
            raise ValidationDomainError("result must be a ReasoningPipelineResult.")
        if not isinstance(rules, tuple) or any(not isinstance(rule, InferenceRule) for rule in rules):
            raise ValidationDomainError("rules must be a tuple of InferenceRule instances.")
        if not all(self._assessment_verifier.verify(item) for item in result.assessments):
            return False
        expected_eligible = tuple(
            item.claim_id for item in result.assessments
            if item.status is AssessmentStatus.SUPPORTED
        )
        if result.eligible_seed_claim_ids != expected_eligible:
            return False
        if result.inference.input_claim_ids != expected_eligible:
            return False
        return self._derivation_verifier.verify(result.inference, rules)
