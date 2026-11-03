from dataclasses import replace

from synapse.domain.claims import Claim
from synapse.domain.contracts import EvidenceArtifact
from synapse.domain.evidence import EvidenceLink, EvidenceRole
from synapse.domain.provenance import Provenance
from synapse.knowledge.knowledge_graph import KnowledgeGraph
from synapse.reasoning.assessment.models import AssessmentStatus
from synapse.reasoning.inference.models import InferenceRule
from synapse.reasoning.pipeline import ReasoningPipeline, ReasoningPipelineVerifier


def make_claim(graph, role, claim_id):
    provenance = Provenance(source="unit-test", method="fixture")
    claim = Claim(proposition=f"proposition {claim_id}", id=claim_id, provenance=provenance)
    artifact = EvidenceArtifact(source="test evidence", content_sha256=EvidenceArtifact.hash_content(claim_id.encode()))
    graph.add_claim(claim)
    graph.add_artifact(artifact)
    graph.add_evidence_link(EvidenceLink(
        claim_id=claim.id, artifact_id=artifact.id, role=role, provenance=provenance
    ))
    return claim


def test_pipeline_only_uses_supported_claims_as_seeds():
    graph = KnowledgeGraph()
    supported = make_claim(graph, EvidenceRole.SUPPORTS, "supported-claim")
    conflicted = make_claim(graph, EvidenceRole.CONTRADICTS, "conflicted-claim")
    provenance = Provenance(source="unit-test", method="fixture")
    artifact = EvidenceArtifact(source="support", content_sha256=EvidenceArtifact.hash_content(b"conflict support"))
    graph.add_artifact(artifact)
    graph.add_evidence_link(EvidenceLink(
        claim_id=conflicted.id, artifact_id=artifact.id, role=EvidenceRole.SUPPORTS, provenance=provenance
    ))

    rules = (
        InferenceRule("from-supported", (supported.id,), "conclusion from supported claim"),
        InferenceRule("from-conflicted", (conflicted.id,), "should not be derived"),
    )
    result = ReasoningPipeline(graph).run((supported.id, conflicted.id), rules, max_depth=2)

    assert [item.status for item in result.assessments] == [AssessmentStatus.SUPPORTED, AssessmentStatus.CONFLICTED]
    assert result.eligible_seed_claim_ids == (supported.id,)
    assert [step.rule_id for step in result.inference.derivations] == ["from-supported"]
    assert result.verification_passed
    assert ReasoningPipelineVerifier(graph).verify(result, rules)


def test_pipeline_verifier_rejects_seed_tampering():
    graph = KnowledgeGraph()
    claim = make_claim(graph, EvidenceRole.SUPPORTS, "seed")
    rules = (InferenceRule("rule", (claim.id,), "derived conclusion"),)
    result = ReasoningPipeline(graph).run((claim.id,), rules)
    tampered = replace(result, eligible_seed_claim_ids=())
    assert not ReasoningPipelineVerifier(graph).verify(tampered, rules)


def test_contradicted_and_inconclusive_claims_are_not_seeds():
    graph = KnowledgeGraph()
    contradicted = make_claim(graph, EvidenceRole.CONTRADICTS, "against")
    inconclusive = Claim(proposition="no evidence", id="no-evidence", provenance=Provenance(source="unit-test", method="fixture"))
    graph.add_claim(inconclusive)
    rules = (InferenceRule("rule", (contradicted.id,), "not inferred"),)
    result = ReasoningPipeline(graph).run((contradicted.id, inconclusive.id), rules)
    assert result.eligible_seed_claim_ids == ()
    assert result.inference.derivations == ()
    assert result.verification_passed
