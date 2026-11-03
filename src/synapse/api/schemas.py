"""Pydantic schemas for the SYNAPSE API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from synapse.domain.state import TaskState


class ObjectiveCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    success_criteria: list[str] = Field(min_length=1)
    description: str = Field(default="", max_length=10000)


class ObjectiveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: str
    success_criteria: list[str]
    created_at: datetime
    revision: int


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    dependencies: list[str] = Field(default_factory=list)


class TaskResponse(BaseModel):
    id: str
    objective_id: str
    title: str
    description: str
    dependencies: list[str]
    created_at: datetime
    revision: int


class TaskStateTransitionRequest(BaseModel):
    target_state: TaskState
    expected_revision: int = Field(ge=0, strict=True)


class InferenceRuleRequest(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    premise_ids: list[str] = Field(min_length=1, max_length=100)
    conclusion: str = Field(min_length=1, max_length=500)


class ReasoningRunRequest(BaseModel):
    claim_ids: list[str] = Field(min_length=1, max_length=500)
    rules: list[InferenceRuleRequest] = Field(default_factory=list, max_length=500)
    max_depth: int = Field(default=3, ge=0, le=10, strict=True)


class EvidenceAssessmentResponse(BaseModel):
    claim_id: str
    status: str
    supporting_link_ids: list[str]
    contradicting_link_ids: list[str]
    contextual_link_ids: list[str]


class DerivationStepResponse(BaseModel):
    id: str
    rule_id: str
    premise_ids: list[str]
    conclusion: str
    depth: int


class InferenceResultResponse(BaseModel):
    input_claim_ids: list[str]
    derivations: list[DerivationStepResponse]
    max_depth: int
    derived_ids: list[str]


class ReasoningRunResponse(BaseModel):
    assessments: list[EvidenceAssessmentResponse]
    inference: InferenceResultResponse
    eligible_seed_claim_ids: list[str]
    assessment_verification_passed: bool
    derivation_verification_passed: bool
    verification_passed: bool
