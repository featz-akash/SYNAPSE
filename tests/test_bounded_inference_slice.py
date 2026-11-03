from dataclasses import replace
import pytest

from synapse.domain.errors import ValidationDomainError
from synapse.reasoning.inference import BoundedInferenceEngine, DerivationVerifier, InferenceRule


def test_rule_fires_and_verifies():
    rules = (
        InferenceRule("r1", ("claim-a",), "derived proposition one"),
        InferenceRule("r2", ("derived:r1",), "derived proposition two"),
    )
    result = BoundedInferenceEngine().infer(("claim-a",), rules, max_depth=2)
    assert [step.depth for step in result.derivations] == [1, 2]
    assert DerivationVerifier().verify(result, rules)


def test_depth_bound_stops_long_chain():
    rules = (
        InferenceRule("r1", ("a",), "one"),
        InferenceRule("r2", ("derived:r1",), "two"),
    )
    result = BoundedInferenceEngine().infer(("a",), rules, max_depth=1)
    assert [step.rule_id for step in result.derivations] == ["r1"]
    assert DerivationVerifier().verify(result, rules)


def test_unseeded_cycle_does_not_fire():
    rules = (
        InferenceRule("r1", ("derived:r2",), "one"),
        InferenceRule("r2", ("derived:r1",), "two"),
    )
    result = BoundedInferenceEngine().infer(("seed",), rules, max_depth=5)
    assert result.derivations == ()


def test_verifier_rejects_tampered_conclusion():
    rules = (InferenceRule("r1", ("a",), "right"),)
    result = BoundedInferenceEngine().infer(("a",), rules, max_depth=1)
    tampered = replace(result, derivations=(replace(result.derivations[0], conclusion="tampered"),))
    assert not DerivationVerifier().verify(tampered, rules)


def test_invalid_depth_rejected():
    with pytest.raises(ValidationDomainError):
        BoundedInferenceEngine().infer(("a",), (), max_depth=-1)
