from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from synapse.persistence.models import Base
from synapse.persistence.models.execution_claim import ExecutionClaim
from synapse.persistence.repositories.execution_claims import claim_execution
from synapse.persistence.recovery.execution_claim_recovery import (
    list_stale_in_progress_claims,
    mark_stale_claim_unknown,
)
from synapse.persistence.repositories.execution_claims import ExecutionClaimError


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def test_stale_claim_is_listed_and_marked_unknown(session_factory):
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        claim_execution(session, key="stale", action_fingerprint="fp")
        session.query(ExecutionClaim).filter_by(key="stale").update(
            {"updated_at": now - timedelta(hours=2)}
        )

    with session_factory.begin() as session:
        found = list_stale_in_progress_claims(
            session, older_than=now - timedelta(hours=1)
        )
        assert [claim.key for claim in found] == ["stale"]
        claim = mark_stale_claim_unknown(
            session,
            key="stale",
            action_fingerprint="fp",
            older_than=now - timedelta(hours=1),
        )
        assert claim.status == "UNKNOWN"
        assert claim.reason_code == "execution_outcome_uncertain"


def test_fresh_claim_not_listed_or_marked_unknown(session_factory):
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        claim_execution(session, key="fresh", action_fingerprint="fp")

    with session_factory() as session:
        assert list_stale_in_progress_claims(
            session, older_than=now - timedelta(hours=1)
        ) == []
        with pytest.raises(ExecutionClaimError, match="not stale"):
            mark_stale_claim_unknown(
                session,
                key="fresh",
                action_fingerprint="fp",
                older_than=now - timedelta(hours=1),
            )


def test_invalid_cutoff_and_limit_rejected(session_factory):
    with session_factory() as session:
        with pytest.raises(ValueError, match="timezone-aware"):
            list_stale_in_progress_claims(session, older_than=datetime.now())
        with pytest.raises(ValueError, match="limit"):
            list_stale_in_progress_claims(
                session, older_than=datetime.now(UTC), limit=0
            )
