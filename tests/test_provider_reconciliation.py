from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from synapse.persistence.models import Base
from synapse.persistence.models.execution_claim import ExecutionClaim
from synapse.persistence.repositories.execution_claims import claim_execution
from synapse.persistence.recovery.execution_claim_recovery import mark_stale_claim_unknown
from synapse.persistence.reconciliation.provider_reconciliation import (
    ProviderObservation,
    ProviderOutcome,
    apply_provider_observation,
)
from synapse.persistence.repositories.execution_claims import (
    ExecutionClaimConflictError,
    ExecutionClaimError,
)


@pytest.fixture
def factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    f = sessionmaker(bind=engine, expire_on_commit=False)
    yield f
    engine.dispose()


def make_unknown(factory, key="op"):
    now = datetime.now(UTC)
    stale_at = now - timedelta(hours=3)
    cutoff = now - timedelta(hours=2)
    with factory.begin() as s:
        claim_execution(s, key=key, action_fingerprint="fp")
        s.query(ExecutionClaim).filter_by(key=key).update(
            {"updated_at": stale_at}
        )
    with factory.begin() as s:
        return mark_stale_claim_unknown(
            s, key=key, action_fingerprint="fp", older_than=cutoff
        )


def test_provider_completed_resolves_unknown(factory):
    make_unknown(factory)
    with factory.begin() as s:
        result = apply_provider_observation(
            s, key="op", action_fingerprint="fp",
            observation=ProviderObservation(ProviderOutcome.COMPLETED, {"id": 8}),
        )
        assert result.current_status == "COMPLETED"
        assert result.retry_safe is False
        claim = s.get(ExecutionClaim, "op")
        assert claim.result_json == '{"id":8}'


def test_provider_unknown_preserves_uncertainty(factory):
    make_unknown(factory)
    with factory.begin() as s:
        result = apply_provider_observation(
            s, key="op", action_fingerprint="fp",
            observation=ProviderObservation(ProviderOutcome.UNKNOWN),
        )
        assert result.current_status == "UNKNOWN"
        assert result.retry_safe is False


def test_provider_not_executed_is_not_automatically_retried(factory):
    make_unknown(factory)
    with factory.begin() as s:
        result = apply_provider_observation(
            s, key="op", action_fingerprint="fp",
            observation=ProviderObservation(ProviderOutcome.NOT_EXECUTED),
        )
        assert result.current_status == "FAILED"
        assert result.retry_safe is True
        assert s.get(ExecutionClaim, "op").reason_code == "provider_confirmed_not_executed"


def test_fingerprint_mismatch_rejected(factory):
    make_unknown(factory)
    with factory.begin() as s:
        with pytest.raises(ExecutionClaimConflictError):
            apply_provider_observation(
                s, key="op", action_fingerprint="other",
                observation=ProviderObservation(ProviderOutcome.UNKNOWN),
            )


def test_only_unknown_claims_can_be_reconciled(factory):
    with factory.begin() as s:
        claim_execution(s, key="active", action_fingerprint="fp")
    with factory.begin() as s:
        with pytest.raises(ExecutionClaimError, match="requires UNKNOWN"):
            apply_provider_observation(
                s, key="active", action_fingerprint="fp",
                observation=ProviderObservation(ProviderOutcome.UNKNOWN),
            )
