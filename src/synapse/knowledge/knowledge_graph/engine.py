"""In-memory knowledge graph with explicit reference integrity."""

from __future__ import annotations

from collections import deque
from threading import RLock

from synapse.domain.claims import Claim
from synapse.domain.contracts import EvidenceArtifact
from synapse.domain.errors import ResourceNotFoundError, ValidationDomainError
from synapse.domain.evidence import EvidenceLink
from synapse.knowledge.knowledge_graph.entities import Entity
from synapse.knowledge.knowledge_graph.relationships import Relationship


class KnowledgeGraph:
    """
    Thread-safe in-memory graph for SYNAPSE knowledge records.

    This component validates references and provides graph queries.
    It does not assess claim truth, evaluate evidence, or persist data.
    """

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._claims: dict[str, Claim] = {}
        self._artifacts: dict[str, EvidenceArtifact] = {}
        self._relationships: dict[str, Relationship] = {}
        self._evidence_links: dict[str, EvidenceLink] = {}
        self._lock = RLock()

    @staticmethod
    def _require_id(value: object, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationDomainError(
                f"{field_name} must be a non-empty string."
            )
        return value

    @staticmethod
    def _insert(
        collection: dict,
        record: object,
        record_id: str,
        record_type: str,
    ) -> object:
        if record_id in collection:
            raise ValidationDomainError(
                f"{record_type} with ID {record_id!r} already exists.",
                details={
                    "record_type": record_type,
                    "record_id": record_id,
                },
            )

        collection[record_id] = record
        return record

    def add_entity(self, entity: Entity) -> Entity:
        if not isinstance(entity, Entity):
            raise ValidationDomainError("entity must be an Entity.")

        with self._lock:
            self._insert(
                self._entities, entity, entity.id, "Entity"
            )
        return entity

    def add_claim(self, claim: Claim) -> Claim:
        if not isinstance(claim, Claim):
            raise ValidationDomainError("claim must be a Claim.")

        with self._lock:
            self._insert(
                self._claims, claim, claim.id, "Claim"
            )
        return claim

    def add_artifact(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        if not isinstance(artifact, EvidenceArtifact):
            raise ValidationDomainError(
                "artifact must be an EvidenceArtifact."
            )

        with self._lock:
            self._insert(
                self._artifacts, artifact, artifact.id, "EvidenceArtifact"
            )
        return artifact

    def add_relationship(
        self,
        relationship: Relationship,
    ) -> Relationship:
        if not isinstance(relationship, Relationship):
            raise ValidationDomainError(
                "relationship must be a Relationship."
            )

        with self._lock:
            self._require_entity(relationship.source_entity_id)
            self._require_entity(relationship.target_entity_id)

            self._insert(
                self._relationships,
                relationship,
                relationship.id,
                "Relationship",
            )

        return relationship

    def add_evidence_link(self, link: EvidenceLink) -> EvidenceLink:
        if not isinstance(link, EvidenceLink):
            raise ValidationDomainError(
                "link must be an EvidenceLink."
            )

        with self._lock:
            self._require_claim(link.claim_id)
            self._require_artifact(link.artifact_id)

            self._insert(
                self._evidence_links,
                link,
                link.id,
                "EvidenceLink",
            )

        return link

    def get_entity(self, entity_id: str) -> Entity:
        entity_id = self._require_id(entity_id, "entity_id")
        with self._lock:
            return self._require_entity(entity_id)

    def get_claim(self, claim_id: str) -> Claim:
        claim_id = self._require_id(claim_id, "claim_id")
        with self._lock:
            return self._require_claim(claim_id)

    def get_artifact(self, artifact_id: str) -> EvidenceArtifact:
        artifact_id = self._require_id(artifact_id, "artifact_id")
        with self._lock:
            return self._require_artifact(artifact_id)

    def get_relationship(self, relationship_id: str) -> Relationship:
        relationship_id = self._require_id(
            relationship_id, "relationship_id"
        )
        with self._lock:
            relationship = self._relationships.get(relationship_id)

            if relationship is None:
                raise ResourceNotFoundError(
                    "Relationship does not exist.",
                    details={"relationship_id": relationship_id},
                )

            return relationship

    def get_evidence_link(self, link_id: str) -> EvidenceLink:
        link_id = self._require_id(link_id, "link_id")
        with self._lock:
            link = self._evidence_links.get(link_id)

            if link is None:
                raise ResourceNotFoundError(
                    "Evidence link does not exist.",
                    details={"link_id": link_id},
                )

            return link

    def relationships_for(self, entity_id: str) -> tuple[Relationship, ...]:
        entity_id = self._require_id(entity_id, "entity_id")

        with self._lock:
            self._require_entity(entity_id)

            matches = (
                relationship
                for relationship in self._relationships.values()
                if (
                    relationship.source_entity_id == entity_id
                    or relationship.target_entity_id == entity_id
                )
            )
            return tuple(sorted(matches, key=lambda item: item.id))

    def evidence_for_claim(self, claim_id: str) -> tuple[EvidenceLink, ...]:
        claim_id = self._require_id(claim_id, "claim_id")

        with self._lock:
            self._require_claim(claim_id)

            matches = (
                link
                for link in self._evidence_links.values()
                if link.claim_id == claim_id
            )
            return tuple(sorted(matches, key=lambda item: item.id))

    def neighbors(self, entity_id: str) -> tuple[Entity, ...]:
        """Return directly connected entities in either direction."""
        entity_id = self._require_id(entity_id, "entity_id")

        with self._lock:
            self._require_entity(entity_id)
            neighbor_ids: set[str] = set()

            for relationship in self._relationships.values():
                if relationship.source_entity_id == entity_id:
                    neighbor_ids.add(relationship.target_entity_id)

                if relationship.target_entity_id == entity_id:
                    neighbor_ids.add(relationship.source_entity_id)

            return tuple(
                self._entities[item_id]
                for item_id in sorted(neighbor_ids)
            )

    def traverse(
        self,
        start_entity_id: str,
        *,
        max_depth: int = 1,
    ) -> tuple[Entity, ...]:
        """
        Perform deterministic breadth-first traversal.

        Traversal follows relationships in either direction. The starting
        entity is excluded from the returned tuple.
        """
        start_entity_id = self._require_id(
            start_entity_id, "start_entity_id"
        )

        if (
            isinstance(max_depth, bool)
            or not isinstance(max_depth, int)
            or max_depth < 1
        ):
            raise ValidationDomainError(
                "max_depth must be a positive integer."
            )

        with self._lock:
            self._require_entity(start_entity_id)

            visited = {start_entity_id}
            queue = deque([(start_entity_id, 0)])
            discovered: list[str] = []

            adjacency: dict[str, set[str]] = {
                entity_id: set() for entity_id in self._entities
            }

            for relationship in self._relationships.values():
                source = relationship.source_entity_id
                target = relationship.target_entity_id
                adjacency[source].add(target)
                adjacency[target].add(source)

            while queue:
                current_id, depth = queue.popleft()

                if depth >= max_depth:
                    continue

                for neighbor_id in sorted(adjacency[current_id]):
                    if neighbor_id in visited:
                        continue

                    visited.add(neighbor_id)
                    discovered.append(neighbor_id)
                    queue.append((neighbor_id, depth + 1))

            return tuple(
                self._entities[entity_id]
                for entity_id in discovered
            )

    def counts(self) -> dict[str, int]:
        """Return a snapshot of graph record counts."""
        with self._lock:
            return {
                "entities": len(self._entities),
                "claims": len(self._claims),
                "artifacts": len(self._artifacts),
                "relationships": len(self._relationships),
                "evidence_links": len(self._evidence_links),
            }

    def _require_entity(self, entity_id: str) -> Entity:
        entity = self._entities.get(entity_id)
        if entity is None:
            raise ResourceNotFoundError(
                "Entity does not exist.",
                details={"entity_id": entity_id},
            )
        return entity

    def _require_claim(self, claim_id: str) -> Claim:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise ResourceNotFoundError(
                "Claim does not exist.",
                details={"claim_id": claim_id},
            )
        return claim

    def _require_artifact(self, artifact_id: str) -> EvidenceArtifact:
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            raise ResourceNotFoundError(
                "Evidence artifact does not exist.",
                details={"artifact_id": artifact_id},
            )
        return artifact