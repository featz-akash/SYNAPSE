import pytest

from synapse.domain.claims import Claim
from synapse.domain.contracts import EvidenceArtifact
from synapse.domain.errors import ResourceNotFoundError, ValidationDomainError
from synapse.domain.evidence import EvidenceLink, EvidenceRole
from synapse.domain.provenance import Provenance
from synapse.knowledge.knowledge_graph import (
    Entity,
    KnowledgeGraph,
    Relationship,
)


@pytest.fixture
def graph() -> KnowledgeGraph:
    return KnowledgeGraph()


@pytest.fixture
def provenance() -> Provenance:
    return Provenance(source="test", method="unit_test")


@pytest.fixture
def earth(provenance: Provenance) -> Entity:
    return Entity(
        canonical_name="Earth",
        entity_type="planet",
        provenance=provenance,
    )


@pytest.fixture
def sun(provenance: Provenance) -> Entity:
    return Entity(
        canonical_name="Sun",
        entity_type="star",
        provenance=provenance,
    )


def test_add_and_get_entity(
    graph: KnowledgeGraph,
    earth: Entity,
) -> None:
    graph.add_entity(earth)
    assert graph.get_entity(earth.id) is earth


def test_duplicate_entity_id_is_rejected(
    graph: KnowledgeGraph,
    earth: Entity,
) -> None:
    graph.add_entity(earth)

    duplicate = Entity(
        canonical_name="Another Earth",
        entity_type="planet",
        id=earth.id,
        provenance=earth.provenance,
    )

    with pytest.raises(ValidationDomainError):
        graph.add_entity(duplicate)


def test_add_and_get_claim(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    claim = Claim(
        proposition="Earth orbits the Sun.",
        provenance=provenance,
    )

    graph.add_claim(claim)
    assert graph.get_claim(claim.id) is claim


def test_add_and_get_artifact(
    graph: KnowledgeGraph,
) -> None:
    artifact = EvidenceArtifact(
        source="research",
        content_sha256=EvidenceArtifact.hash_content(b"observation"),
    )

    graph.add_artifact(artifact)
    assert graph.get_artifact(artifact.id) is artifact


def test_relationship_requires_existing_source(
    graph: KnowledgeGraph,
    sun: Entity,
    provenance: Provenance,
) -> None:
    graph.add_entity(sun)

    relationship = Relationship(
        source_entity_id="missing",
        relationship_type="orbits",
        target_entity_id=sun.id,
        provenance=provenance,
    )

    with pytest.raises(ResourceNotFoundError):
        graph.add_relationship(relationship)

    assert graph.counts()["relationships"] == 0


def test_relationship_requires_existing_target(
    graph: KnowledgeGraph,
    earth: Entity,
    provenance: Provenance,
) -> None:
    graph.add_entity(earth)

    relationship = Relationship(
        source_entity_id=earth.id,
        relationship_type="orbits",
        target_entity_id="missing",
        provenance=provenance,
    )

    with pytest.raises(ResourceNotFoundError):
        graph.add_relationship(relationship)


def test_add_and_get_relationship(
    graph: KnowledgeGraph,
    earth: Entity,
    sun: Entity,
    provenance: Provenance,
) -> None:
    graph.add_entity(earth)
    graph.add_entity(sun)

    relationship = Relationship(
        source_entity_id=earth.id,
        relationship_type="orbits",
        target_entity_id=sun.id,
        provenance=provenance,
    )

    graph.add_relationship(relationship)

    assert graph.get_relationship(relationship.id) is relationship


def test_evidence_link_requires_existing_claim(
    graph: KnowledgeGraph,
) -> None:
    artifact = EvidenceArtifact(
        source="research",
        content_sha256=EvidenceArtifact.hash_content(b"data"),
    )
    graph.add_artifact(artifact)

    link = EvidenceLink(
        claim_id="missing-claim",
        artifact_id=artifact.id,
        role=EvidenceRole.SUPPORTS,
        provenance=Provenance(source="test", method="unit_test"),
    )

    with pytest.raises(ResourceNotFoundError):
        graph.add_evidence_link(link)


def test_evidence_link_requires_existing_artifact(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    claim = Claim(
        proposition="Earth orbits the Sun.",
        provenance=provenance,
    )
    graph.add_claim(claim)

    link = EvidenceLink(
        claim_id=claim.id,
        artifact_id="missing-artifact",
        role=EvidenceRole.SUPPORTS,
        provenance=provenance,
    )

    with pytest.raises(ResourceNotFoundError):
        graph.add_evidence_link(link)


def test_add_and_retrieve_evidence_link(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    claim = Claim(
        proposition="Earth orbits the Sun.",
        provenance=provenance,
    )
    artifact = EvidenceArtifact(
        source="research",
        content_sha256=EvidenceArtifact.hash_content(b"observation"),
    )
    graph.add_claim(claim)
    graph.add_artifact(artifact)

    link = EvidenceLink(
        claim_id=claim.id,
        artifact_id=artifact.id,
        role=EvidenceRole.SUPPORTS,
        provenance=provenance,
    )

    graph.add_evidence_link(link)

    assert graph.get_evidence_link(link.id) is link
    assert graph.evidence_for_claim(claim.id) == (link,)


def test_neighbors_returns_direct_connections(
    graph: KnowledgeGraph,
    earth: Entity,
    sun: Entity,
    provenance: Provenance,
) -> None:
    graph.add_entity(earth)
    graph.add_entity(sun)

    graph.add_relationship(
        Relationship(
            source_entity_id=earth.id,
            relationship_type="orbits",
            target_entity_id=sun.id,
            provenance=provenance,
        )
    )

    assert graph.neighbors(earth.id) == (sun,)
    assert graph.neighbors(sun.id) == (earth,)


def test_traverse_respects_max_depth(
    graph: KnowledgeGraph,
    provenance: Provenance,
) -> None:
    earth = Entity("Earth", "planet", provenance, id="earth")
    sun = Entity("Sun", "star", provenance, id="sun")
    galaxy = Entity("Milky Way", "galaxy", provenance, id="galaxy")

    for entity in (earth, sun, galaxy):
        graph.add_entity(entity)

    graph.add_relationship(
        Relationship("earth", "orbits", "sun", provenance)
    )
    graph.add_relationship(
        Relationship("sun", "located_in", "galaxy", provenance)
    )

    assert graph.traverse("earth", max_depth=1) == (sun,)
    assert set(graph.traverse("earth", max_depth=2)) == {sun, galaxy}


@pytest.mark.parametrize("max_depth", [0, -1, True, 1.5])
def test_traverse_rejects_invalid_depth(
    graph: KnowledgeGraph,
    earth: Entity,
    max_depth: object,
) -> None:
    graph.add_entity(earth)

    with pytest.raises(ValidationDomainError):
        graph.traverse(earth.id, max_depth=max_depth)  # type: ignore[arg-type]


def test_graph_counts(
    graph: KnowledgeGraph,
    earth: Entity,
) -> None:
    graph.add_entity(earth)

    assert graph.counts() == {
        "entities": 1,
        "claims": 0,
        "artifacts": 0,
        "relationships": 0,
        "evidence_links": 0,
    }


def test_missing_entity_raises_not_found(
    graph: KnowledgeGraph,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        graph.get_entity("missing")


def test_graph_rejects_invalid_record_type(
    graph: KnowledgeGraph,
) -> None:
    with pytest.raises(ValidationDomainError):
        graph.add_entity(None)  # type: ignore[arg-type]


def test_failed_relationship_does_not_modify_graph(
    graph: KnowledgeGraph,
    earth: Entity,
    provenance: Provenance,
) -> None:
    graph.add_entity(earth)

    with pytest.raises(ResourceNotFoundError):
        graph.add_relationship(
            Relationship(
                source_entity_id=earth.id,
                relationship_type="connected_to",
                target_entity_id="missing",
                provenance=provenance,
            )
        )

    assert graph.counts()["relationships"] == 0