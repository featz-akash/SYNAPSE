"""Core SYNAPSE domain contracts and state machines."""

from synapse.domain.contracts import (
    EvidenceArtifact,
    Objective,
    ProposedAction,
    Task,
)
from synapse.domain.state import ObjectiveState, TaskState
from synapse.domain.claims import Claim
from synapse.domain.provenance import Provenance
from synapse.domain.evidence import EvidenceLink, EvidenceRole

__all__ = [
    "EvidenceArtifact",
    "Objective",
    "ObjectiveState",
    "ProposedAction",
    "Task",
    "TaskState",
    "Claim",
    "Provenance",
]
