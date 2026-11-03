"""Contracts for bounded, rule-driven symbolic inference."""
from __future__ import annotations

from dataclasses import dataclass
from synapse.domain.errors import ValidationDomainError


def _nonblank(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationDomainError(f"{field} must be a non-empty string.")


@dataclass(frozen=True, slots=True)
class InferenceRule:
    """An explicit rule: all listed premise IDs imply a proposition.

    Premise IDs may reference input claims or conclusions from other rules.
    This contract does not encode probabilistic or open-world semantics.
    """
    id: str
    premise_ids: tuple[str, ...]
    conclusion: str

    def __post_init__(self) -> None:
        _nonblank(self.id, "rule id")
        _nonblank(self.conclusion, "conclusion")
        if not isinstance(self.premise_ids, tuple) or not self.premise_ids:
            raise ValidationDomainError("premise_ids must be a non-empty tuple.")
        for premise in self.premise_ids:
            _nonblank(premise, "premise id")
        if len(set(self.premise_ids)) != len(self.premise_ids):
            raise ValidationDomainError("premise_ids must be unique.")


@dataclass(frozen=True, slots=True)
class DerivationStep:
    """Auditable record of one rule firing; conclusion is derived, not observed."""
    id: str
    rule_id: str
    premise_ids: tuple[str, ...]
    conclusion: str
    depth: int


@dataclass(frozen=True, slots=True)
class InferenceResult:
    input_claim_ids: tuple[str, ...]
    derivations: tuple[DerivationStep, ...]
    max_depth: int

    @property
    def derived_ids(self) -> tuple[str, ...]:
        return tuple(step.id for step in self.derivations)
