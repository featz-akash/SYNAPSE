from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from synapse.domain.contracts import EvidenceArtifact
from synapse.domain.errors import ValidationDomainError
from synapse.domain.evidence import EvidenceLink, EvidenceRole
from synapse.domain.provenance import Provenance
from synapse.knowledge.knowledge_graph import Entity, Relationship


@pytest.fixture
def provenance() -> Provenance:
    return Provenance(
        source="test_source",
        method="manual_entry",
    )


@pytest.fixture
def earth(provenance: Provenance) -> Entity:
    return Entity(
        canonical_name="Earth",
        entity_type="planet",
        aliases=("Terra",),
        provenance=provenance,
    )


@pytest.fixture
def sun(provenance: Provenance) -> Entity:
    return Entity(
        canonical_name="Sun",
        entity_type="star",
        provenance=provenance,
    )


def test_entity_creation(earth: Entity) -> None:
    assert earth.canonical_name == "Earth"
    assert earth.entity_type == "planet"
    assert earth.aliases == ("Terra",)
    assert earth.id


def test_entity_rejects_blank_name(provenance: Provenance) -> None:
    with pytest.raises(ValidationDomainError):
        Entity(
            canonical_name=" ",
            entity_type="planet",
            provenance=provenance,
        )


def test_entity_rejects_duplicate_aliases(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        Entity(
            canonical_name="Earth",
            entity_type="planet",
            aliases=("Terra", "terra"),
            provenance=provenance,
        )


def test_entity_rejects_canonical_name_as_alias(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        Entity(
            canonical_name="Earth",
            entity_type="planet",
            aliases=("earth",),
            provenance=provenance,
        )


def test_entity_requires_provenance() -> None:
    with pytest.raises(ValidationDomainError):
        Entity(
            canonical_name="Earth",
            entity_type="planet",
            provenance=None,  # type: ignore[arg-type]
        )


def test_entity_rejects_naive_timestamp(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        Entity(
            canonical_name="Earth",
            entity_type="planet",
            provenance=provenance,
            created_at=datetime(2026, 1, 1),
        )


def test_entity_is_immutable(earth: Entity) -> None:
    with pytest.raises(FrozenInstanceError):
        earth.canonical_name = "Mars"  # type: ignore[misc]


def test_relationship_creation(
    earth: Entity,
    sun: Entity,
    provenance: Provenance,
) -> None:
    relationship = Relationship(
        source_entity_id=earth.id,
        relationship_type="orbits",
        target_entity_id=sun.id,
        provenance=provenance,
    )

    assert relationship.source_entity_id == earth.id
    assert relationship.target_entity_id == sun.id
    assert relationship.relationship_type == "orbits"


def test_relationship_is_directed(
    earth: Entity,
    sun: Entity,
    provenance: Provenance,
) -> None:
    forward = Relationship(
        source_entity_id=earth.id,
        relationship_type="orbits",
        target_entity_id=sun.id,
        provenance=provenance,
    )

    reverse = Relationship(
        source_entity_id=sun.id,
        relationship_type="orbits",
        target_entity_id=earth.id,
        provenance=provenance,
    )

    assert forward.source_entity_id != reverse.source_entity_id


def test_relationship_rejects_blank_endpoint(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        Relationship(
            source_entity_id=" ",
            relationship_type="orbits",
            target_entity_id="sun-1",
            provenance=provenance,
        )


def test_relationship_rejects_invalid_provenance() -> None:
    with pytest.raises(ValidationDomainError):
        Relationship(
            source_entity_id="earth-1",
            relationship_type="orbits",
            target_entity_id="sun-1",
            provenance=None,  # type: ignore[arg-type]
        )


def test_evidence_link_creation(
    provenance: Provenance,
) -> None:
    link = EvidenceLink(
        claim_id="claim-1",
        artifact_id="artifact-1",
        role=EvidenceRole.SUPPORTS,
        provenance=provenance,
    )

    assert link.claim_id == "claim-1"
    assert link.artifact_id == "artifact-1"
    assert link.role is EvidenceRole.SUPPORTS


@pytest.mark.parametrize(
    "role",
    [
        EvidenceRole.SUPPORTS,
        EvidenceRole.CONTRADICTS,
        EvidenceRole.CONTEXTUAL,
    ],
)
def test_evidence_link_roles(
    role: EvidenceRole,
    provenance: Provenance,
) -> None:
    link = EvidenceLink(
        claim_id="claim-1",
        artifact_id="artifact-1",
        role=role,
        provenance=provenance,
    )

    assert link.role is role


def test_evidence_link_rejects_string_role(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        EvidenceLink(
            claim_id="claim-1",
            artifact_id="artifact-1",
            role="supports",  # type: ignore[arg-type]
            provenance=provenance,
        )


def test_evidence_link_rejects_missing_artifact_id(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        EvidenceLink(
            claim_id="claim-1",
            artifact_id=" ",
            role=EvidenceRole.SUPPORTS,
            provenance=provenance,
        )


def test_evidence_link_rejects_naive_timestamp(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        EvidenceLink(
            claim_id="claim-1",
            artifact_id="artifact-1",
            role=EvidenceRole.SUPPORTS,
            provenance=provenance,
            linked_at=datetime(2026, 1, 1),
        )


def test_evidence_artifact_can_be_referenced(
    provenance: Provenance,
) -> None:
    artifact = EvidenceArtifact(
        source="research_document",
        content_sha256=EvidenceArtifact.hash_content(b"Earth orbits the Sun"),
    )

    link = EvidenceLink(
        claim_id="claim-1",
        artifact_id=artifact.id,
        role=EvidenceRole.SUPPORTS,
        provenance=provenance,
    )

    assert link.artifact_id == artifact.id


def test_evidence_link_is_immutable(
    provenance: Provenance,
) -> None:
    link = EvidenceLink(
        claim_id="claim-1",
        artifact_id="artifact-1",
        role=EvidenceRole.CONTEXTUAL,
        provenance=provenance,
    )

    with pytest.raises(FrozenInstanceError):
        link.role = EvidenceRole.SUPPORTS  # type: ignore[misc]