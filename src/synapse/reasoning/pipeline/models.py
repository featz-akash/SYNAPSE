"""Result contract for a composed, non-mutating reasoning run."""
from __future__ import annotations
from dataclasses import dataclass
from synapse.reasoning.assessment.models import EvidenceAssessment
from synapse.reasoning.inference.models import InferenceResult

@dataclass(frozen=True, slots=True)
class ReasoningPipelineResult:
    assessments: tuple[EvidenceAssessment, ...]
    inference: InferenceResult
    eligible_seed_claim_ids: tuple[str, ...]
    assessment_verification_passed: bool
    derivation_verification_passed: bool

    @property
    def verification_passed(self) -> bool:
        return self.assessment_verification_passed and self.derivation_verification_passed
