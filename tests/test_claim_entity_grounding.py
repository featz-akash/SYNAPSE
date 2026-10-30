import pytest

from synapse.domain.claims import (
    Claim,
    ClaimEntityGrounding,
    ClaimEntityRole,
)
from synapse.domain.errors import ResourceNotFoundError, ValidationDomainError
from synapse.domain.provenance import Provenance
from synapse.knowledge.knowledge_graph import Entity, KnowledgeGraph


@pytest.fixture
def provenance() -> Provenance:
    return Provenance(source="test", method="unit_test")


@pytest.fixture
def graph(provenance: Provenance) -> KnowledgeGraph:
    graph = KnowledgeGraph()

    claim = Claim(
        proposition="Earth orbits the Sun.",
        provenance=provenance,
        id="claim-earth-orbit",
    )
    earth = Entity(
        canonical_name="Earth",
        entity_type="planet",
        provenance=provenance,
        id="entity-earth",
    )
    sun = Entity(
        canonical_name="Sun",
        entity_type="star",
        provenance=provenance,
        id="entity-sun",
    )

    graph.add_claim(claim)
    graph.add_entity(earth)
    graph.add_entity(sun)

    return graph


def test_add_and_retrieve_subject_grounding(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    grounding = ClaimEntityGrounding(
        claim_id="claim-earth-orbit",
        entity_id="entity-earth",
        mention_text="Earth",
        role=ClaimEntityRole.SUBJECT,
        provenance=provenance,
        start_char=0,
        end_char=5,
    )

    graph.add_claim_entity_grounding(grounding)

    assert graph.get_claim_entity_grounding(grounding.id) == grounding
    assert graph.groundings_for_claim("claim-earth-orbit") == (grounding,)


def test_add_object_grounding(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    grounding = ClaimEntityGrounding(
        claim_id="claim-earth-orbit",
        entity_id="entity-sun",
        mention_text="Sun",
        role=ClaimEntityRole.OBJECT,
        provenance=provenance,
        start_char=17,
        end_char=20,
    )

    graph.add_claim_entity_grounding(grounding)

    assert graph.groundings_for_claim("claim-earth-orbit") == (grounding,)


def test_grounding_requires_existing_claim(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    grounding = ClaimEntityGrounding(
        claim_id="missing-claim",
        entity_id="entity-earth",
        mention_text="Earth",
        role=ClaimEntityRole.SUBJECT,
        provenance=provenance,
    )

    with pytest.raises(ResourceNotFoundError):
        graph.add_claim_entity_grounding(grounding)


def test_grounding_requires_existing_entity(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    grounding = ClaimEntityGrounding(
        claim_id="claim-earth-orbit",
        entity_id="missing-entity",
        mention_text="Earth",
        role=ClaimEntityRole.SUBJECT,
        provenance=provenance,
    )

    with pytest.raises(ResourceNotFoundError):
        graph.add_claim_entity_grounding(grounding)


def test_grounding_rejects_incorrect_text_span(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    grounding = ClaimEntityGrounding(
        claim_id="claim-earth-orbit",
        entity_id="entity-earth",
        mention_text="Mars",
        role=ClaimEntityRole.SUBJECT,
        provenance=provenance,
        start_char=0,
        end_char=4,
    )

    with pytest.raises(ValidationDomainError):
        graph.add_claim_entity_grounding(grounding)

    assert graph.counts()["claim_entity_groundings"] == 0


def test_grounding_rejects_duplicate_id(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    grounding = ClaimEntityGrounding(
        claim_id="claim-earth-orbit",
        entity_id="entity-earth",
        mention_text="Earth",
        role=ClaimEntityRole.SUBJECT,
        provenance=provenance,
        id="grounding-1",
    )

    graph.add_claim_entity_grounding(grounding)

    duplicate = ClaimEntityGrounding(
        claim_id="claim-earth-orbit",
        entity_id="entity-sun",
        mention_text="Sun",
        role=ClaimEntityRole.OBJECT,
        provenance=provenance,
        id="grounding-1",
    )

    with pytest.raises(ValidationDomainError):
        graph.add_claim_entity_grounding(duplicate)


def test_grounding_rejects_incomplete_span(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValueError):
        ClaimEntityGrounding(
            claim_id="claim-1",
            entity_id="entity-1",
            mention_text="Earth",
            role=ClaimEntityRole.SUBJECT,
            provenance=provenance,
            start_char=0,
        )


def test_grounding_rejects_span_length_mismatch(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValueError):
        ClaimEntityGrounding(
            claim_id="claim-1",
            entity_id="entity-1",
            mention_text="Earth",
            role=ClaimEntityRole.SUBJECT,
            provenance=provenance,
            start_char=0,
            end_char=4,
        )


def test_grounding_requires_valid_role(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValueError):
        ClaimEntityGrounding(
            claim_id="claim-1",
            entity_id="entity-1",
            mention_text="Earth",
            role="subject",  # type: ignore[arg-type]
            provenance=provenance,
        )


def test_grounding_without_offsets_is_allowed(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    grounding = ClaimEntityGrounding(
        claim_id="claim-earth-orbit",
        entity_id="entity-earth",
        mention_text="Earth",
        role=ClaimEntityRole.SUBJECT,
        provenance=provenance,
    )

    graph.add_claim_entity_grounding(grounding)

    assert graph.groundings_for_claim("claim-earth-orbit") == (grounding,)


def test_grounding_counts(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    grounding = ClaimEntityGrounding(
        claim_id="claim-earth-orbit",
        entity_id="entity-earth",
        mention_text="Earth",
        role=ClaimEntityRole.SUBJECT,
        provenance=provenance,
    )
    graph.add_claim_entity_grounding(grounding)

    assert graph.counts()["claim_entity_groundings"] == 1