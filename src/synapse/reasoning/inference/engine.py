"""Deterministic bounded inference over explicitly supplied rules."""
from __future__ import annotations

from synapse.domain.errors import ValidationDomainError
from synapse.reasoning.inference.models import DerivationStep, InferenceRule, InferenceResult


class BoundedInferenceEngine:
    """Apply explicit rules to a finite set of claim IDs up to a depth bound.

    This engine creates derivation records only. It does not mutate the graph,
    assert real-world truth, or infer rules from natural-language text.
    """
    def infer(
        self,
        claim_ids: tuple[str, ...],
        rules: tuple[InferenceRule, ...],
        *,
        max_depth: int = 3,
    ) -> InferenceResult:
        if not isinstance(claim_ids, tuple) or any(not isinstance(x, str) or not x.strip() for x in claim_ids):
            raise ValidationDomainError("claim_ids must be a tuple of non-empty strings.")
        if len(set(claim_ids)) != len(claim_ids):
            raise ValidationDomainError("claim_ids must be unique.")
        if not isinstance(rules, tuple) or any(not isinstance(r, InferenceRule) for r in rules):
            raise ValidationDomainError("rules must be a tuple of InferenceRule instances.")
        if len({r.id for r in rules}) != len(rules):
            raise ValidationDomainError("rule IDs must be unique.")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
            raise ValidationDomainError("max_depth must be a non-negative integer.")

        known: dict[str, int] = {cid: 0 for cid in claim_ids}
        steps: list[DerivationStep] = []
        fired: set[str] = set()
        # Each pass can add at most a finite number of conclusions (one per rule).
        for _ in range(max_depth):
            changed = False
            for rule in sorted(rules, key=lambda r: r.id):
                if rule.id in fired or not all(pid in known for pid in rule.premise_ids):
                    continue
                depth = 1 + max(known[pid] for pid in rule.premise_ids)
                if depth > max_depth:
                    continue
                # Rule IDs uniquely name firings in this deliberately simple contract.
                step_id = f"derived:{rule.id}"
                if step_id in known:
                    fired.add(rule.id)
                    continue
                step = DerivationStep(step_id, rule.id, rule.premise_ids, rule.conclusion, depth)
                steps.append(step)
                known[step_id] = depth
                fired.add(rule.id)
                changed = True
            if not changed:
                break
        return InferenceResult(tuple(claim_ids), tuple(steps), max_depth)
