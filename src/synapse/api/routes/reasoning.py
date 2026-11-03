"""Read-only HTTP endpoint for evidence assessment and bounded inference."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from synapse.api.dependencies import require_permission
from synapse.api.errors import domain_error_to_http_exception
from synapse.api.schemas import (
    DerivationStepResponse,
    EvidenceAssessmentResponse,
    InferenceResultResponse,
    ReasoningRunRequest,
    ReasoningRunResponse,
)
from synapse.domain.errors import DomainError
from synapse.knowledge.knowledge_graph.engine import KnowledgeGraph
from synapse.reasoning.inference.models import InferenceRule
from synapse.reasoning.pipeline.engine import ReasoningPipeline

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


@router.post(
    "/run",
    response_model=ReasoningRunResponse,
)
def run_reasoning(
    payload: ReasoningRunRequest,
    request: Request,
    _principal: Annotated[object, Depends(require_permission("reasoning:run"))],
) -> ReasoningRunResponse:
    """Assess supplied graph claims and infer from supported seeds only.

    This endpoint does not modify the graph and cannot trigger external actions.
    """
    graph: KnowledgeGraph | None = getattr(
        request.app.state, "reasoning_graph", None
    )
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reasoning graph is not configured.",
        )

    rules = tuple(
        InferenceRule(
            id=rule.id,
            premise_ids=tuple(rule.premise_ids),
            conclusion=rule.conclusion,
        )
        for rule in payload.rules
    )

    try:
        result = ReasoningPipeline(graph).run(
            tuple(payload.claim_ids),
            rules,
            max_depth=payload.max_depth,
        )
    except DomainError as exc:
        raise domain_error_to_http_exception(exc) from exc

    return ReasoningRunResponse(
        assessments=[
            EvidenceAssessmentResponse(
                claim_id=item.claim_id,
                status=item.status.value,
                supporting_link_ids=list(item.supporting_link_ids),
                contradicting_link_ids=list(item.contradicting_link_ids),
                contextual_link_ids=list(item.contextual_link_ids),
            )
            for item in result.assessments
        ],
        inference=InferenceResultResponse(
            input_claim_ids=list(result.inference.input_claim_ids),
            derivations=[
                DerivationStepResponse(
                    id=step.id,
                    rule_id=step.rule_id,
                    premise_ids=list(step.premise_ids),
                    conclusion=step.conclusion,
                    depth=step.depth,
                )
                for step in result.inference.derivations
            ],
            max_depth=result.inference.max_depth,
            derived_ids=list(result.inference.derived_ids),
        ),
        eligible_seed_claim_ids=list(result.eligible_seed_claim_ids),
        assessment_verification_passed=result.assessment_verification_passed,
        derivation_verification_passed=result.derivation_verification_passed,
        verification_passed=result.verification_passed,
    )
