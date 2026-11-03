"""Typed output contract for evidence-link assessment."""
from dataclasses import dataclass
from enum import StrEnum

class AssessmentStatus(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    CONFLICTED = "conflicted"
    INCONCLUSIVE = "inconclusive"

@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    claim_id: str
    status: AssessmentStatus
    supporting_link_ids: tuple[str, ...]
    contradicting_link_ids: tuple[str, ...]
    contextual_link_ids: tuple[str, ...]

    @property
    def all_link_ids(self) -> tuple[str, ...]:
        return self.supporting_link_ids + self.contradicting_link_ids + self.contextual_link_ids
