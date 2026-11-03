"""Independent structural verifier for bounded inference results."""
from __future__ import annotations
from synapse.domain.errors import ValidationDomainError
from synapse.reasoning.inference.models import InferenceResult, InferenceRule


class DerivationVerifier:
    def verify(self, result: InferenceResult, rules: tuple[InferenceRule, ...]) -> bool:
        if not isinstance(result, InferenceResult):
            raise ValidationDomainError("result must be an InferenceResult.")
        if not isinstance(rules, tuple) or any(not isinstance(r, InferenceRule) for r in rules):
            raise ValidationDomainError("rules must be a tuple of InferenceRule instances.")
        by_id = {rule.id: rule for rule in rules}
        known = {cid: 0 for cid in result.input_claim_ids}
        seen_rules: set[str] = set()
        for step in result.derivations:
            rule = by_id.get(step.rule_id)
            if rule is None or step.rule_id in seen_rules:
                return False
            if step.id != f"derived:{rule.id}" or step.premise_ids != rule.premise_ids or step.conclusion != rule.conclusion:
                return False
            if not all(pid in known for pid in step.premise_ids):
                return False
            expected_depth = 1 + max(known[pid] for pid in step.premise_ids)
            if step.depth != expected_depth or step.depth > result.max_depth:
                return False
            if step.id in known:
                return False
            known[step.id] = step.depth
            seen_rules.add(step.rule_id)
        return True
