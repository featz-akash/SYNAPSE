from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from synapse.domain.claims import Claim
from synapse.domain.errors import ValidationDomainError
from synapse.domain.provenance import Provenance


@pytest.fixture
def provenance() -> Provenance:
    return Provenance(
        source="user_input",
        method="direct_submission",
        actor="user",
    )


def test_provenance_creation() -> None:
    record = Provenance(
        source="research_document",
        method="document_extraction",
        actor="document_processor",
        source_reference="document-001",
    )

    assert record.source == "research_document"
    assert record.method == "document_extraction"
    assert record.id


def test_provenance_rejects_blank_source() -> None:
    with pytest.raises(ValidationDomainError):
        Provenance(source=" ", method="manual_entry")


def test_provenance_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationDomainError):
        Provenance(
            source="test",
            method="manual",
            recorded_at=datetime(2026, 1, 1),
        )


def test_provenance_rejects_duplicate_parent_ids() -> None:
    with pytest.raises(ValidationDomainError):
        Provenance(
            source="test",
            method="derived",
            parent_record_ids=("record-1", "record-1"),
        )


def test_claim_creation(provenance: Provenance) -> None:
    claim = Claim(
        proposition="Earth orbits the Sun.",
        provenance=provenance,
    )

    assert claim.proposition == "Earth orbits the Sun."
    assert claim.provenance is provenance
    assert claim.id


def test_claim_supports_scope_and_normalized_text(
    provenance: Provenance,
) -> None:
    claim = Claim(
        proposition="Earth orbits the Sun.",
        normalized_text="earth orbits sun",
        scope="Solar System",
        provenance=provenance,
    )

    assert claim.normalized_text == "earth orbits sun"
    assert claim.scope == "Solar System"


def test_claim_rejects_blank_proposition(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        Claim(proposition=" ", provenance=provenance)


def test_claim_requires_provenance() -> None:
    with pytest.raises(ValidationDomainError):
        Claim(
            proposition="A test assertion",
            provenance=None,  # type: ignore[arg-type]
        )


def test_claim_rejects_naive_datetime(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValidationDomainError):
        Claim(
            proposition="A test assertion",
            provenance=provenance,
            created_at=datetime(2026, 1, 1),
        )


def test_claim_is_immutable(provenance: Provenance) -> None:
    claim = Claim(
        proposition="A test assertion",
        provenance=provenance,
    )

    with pytest.raises(FrozenInstanceError):
        claim.proposition = "Modified assertion"  # type: ignore[misc]


def test_provenance_is_immutable() -> None:
    record = Provenance(
        source="user_input",
        method="direct_submission",
    )

    with pytest.raises(FrozenInstanceError):
        record.source = "modified"  # type: ignore[misc]


def test_claim_does_not_imply_truth(
    provenance: Provenance,
) -> None:
    claim = Claim(
        proposition="An unverified assertion.",
        provenance=provenance,
    )

    # Creating a claim does not assign it a truth or belief status.
    assert not hasattr(claim, "confidence")
    assert not hasattr(claim, "is_true")