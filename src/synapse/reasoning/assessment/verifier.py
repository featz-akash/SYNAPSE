"""Independent structural checks for evidence assessments."""
from synapse.domain.errors import ValidationDomainError
from synapse.domain.evidence import EvidenceRole
from synapse.knowledge.knowledge_graph.engine import KnowledgeGraph
from synapse.reasoning.assessment.models import AssessmentStatus, EvidenceAssessment

class EvidenceAssessmentVerifier:
    def __init__(self, graph: KnowledgeGraph) -> None:
        if not isinstance(graph, KnowledgeGraph):
            raise ValidationDomainError("graph must be a KnowledgeGraph.")
        self._graph = graph

    def verify(self, result: EvidenceAssessment) -> bool:
        if not isinstance(result, EvidenceAssessment):
            raise ValidationDomainError("result must be an EvidenceAssessment.")
        links = self._graph.evidence_for_claim(result.claim_id)
        actual = {link.id: link.role for link in links}
        groups = (
            (result.supporting_link_ids, EvidenceRole.SUPPORTS),
            (result.contradicting_link_ids, EvidenceRole.CONTRADICTS),
            (result.contextual_link_ids, EvidenceRole.CONTEXTUAL),
        )
        seen = set()
        for ids, expected_role in groups:
            for link_id in ids:
                if link_id in seen or actual.get(link_id) is not expected_role:
                    return False
                seen.add(link_id)
        if seen != set(actual):
            return False

        support = bool(result.supporting_link_ids)
        contradiction = bool(result.contradicting_link_ids)
        expected = (
            AssessmentStatus.CONFLICTED if support and contradiction else
            AssessmentStatus.SUPPORTED if support else
            AssessmentStatus.CONTRADICTED if contradiction else
            AssessmentStatus.INCONCLUSIVE
        )
        return result.status is expected
