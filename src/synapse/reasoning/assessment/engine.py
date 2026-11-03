"""Deterministic assessment of evidence-link roles (not claim truth)."""
from synapse.domain.evidence import EvidenceRole
from synapse.domain.errors import ValidationDomainError
from synapse.knowledge.knowledge_graph.engine import KnowledgeGraph
from synapse.reasoning.assessment.models import AssessmentStatus, EvidenceAssessment

class EvidenceAssessmentEngine:
    def __init__(self, graph: KnowledgeGraph) -> None:
        if not isinstance(graph, KnowledgeGraph):
            raise ValidationDomainError("graph must be a KnowledgeGraph.")
        self._graph = graph

    def assess(self, claim_id: str) -> EvidenceAssessment:
        # Graph accessor validates that the claim exists and returns stable ordering.
        links = self._graph.evidence_for_claim(claim_id)
        support = tuple(link.id for link in links if link.role is EvidenceRole.SUPPORTS)
        contradiction = tuple(link.id for link in links if link.role is EvidenceRole.CONTRADICTS)
        context = tuple(link.id for link in links if link.role is EvidenceRole.CONTEXTUAL)

        if support and contradiction:
            status = AssessmentStatus.CONFLICTED
        elif support:
            status = AssessmentStatus.SUPPORTED
        elif contradiction:
            status = AssessmentStatus.CONTRADICTED
        else:
            status = AssessmentStatus.INCONCLUSIVE

        return EvidenceAssessment(claim_id, status, support, contradiction, context)
