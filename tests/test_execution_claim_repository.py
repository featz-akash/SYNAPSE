
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from synapse.persistence.models import Base
from synapse.persistence.models.execution_claim import ExecutionClaim
from synapse.persistence.repositories.execution_claims import (
    ExecutionAlreadyInProgressError,
    ExecutionClaimConflictError,
    ExecutionClaimError,
    ExecutionOutcomeUnknownError,
    claim_execution,
    complete_execution,
    fail_execution,
    get_completed_result,
    get_execution_claim,
    mark_execution_unknown,
)


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        yield factory
    finally:
        engine.dispose()


def test_claim_and_complete_persist_result(session_factory):
    with session_factory.begin() as session:
        claim_execution(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
        )

    with session_factory.begin() as session:
        claim = complete_execution(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
            result={"status": "ok", "count": 2},
        )
        assert claim.status == "COMPLETED"

    with session_factory() as session:
        assert get_completed_result(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
        ) == {"count": 2, "status": "ok"}


def test_claim_rejects_conflicting_fingerprint(session_factory):
    with session_factory.begin() as session:
        claim_execution(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
        )

    with session_factory() as session:
        with pytest.raises(ExecutionClaimConflictError):
            claim_execution(
                session,
                key="request-1",
                action_fingerprint="fingerprint-b",
            )


def test_in_progress_claim_cannot_be_claimed_again(session_factory):
    with session_factory.begin() as session:
        claim_execution(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
        )

    with session_factory() as session:
        with pytest.raises(ExecutionAlreadyInProgressError):
            claim_execution(
                session,
                key="request-1",
                action_fingerprint="fingerprint-a",
            )


def test_unknown_claim_requires_reconciliation(session_factory):
    with session_factory.begin() as session:
        claim_execution(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
        )

    with session_factory.begin() as session:
        mark_execution_unknown(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
        )

    with session_factory() as session:
        with pytest.raises(ExecutionOutcomeUnknownError):
            claim_execution(
                session,
                key="request-1",
                action_fingerprint="fingerprint-a",
            )


def test_failed_claim_is_not_silently_retried(session_factory):
    with session_factory.begin() as session:
        claim_execution(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
        )

    with session_factory.begin() as session:
        fail_execution(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
            reason_code="ToolTimeout",
        )

    with session_factory() as session:
        with pytest.raises(ExecutionClaimError):
            claim_execution(
                session,
                key="request-1",
                action_fingerprint="fingerprint-a",
            )


def test_claim_rollback_does_not_persist(session_factory):
    with pytest.raises(RuntimeError, match="force rollback"):
        with session_factory.begin() as session:
            claim_execution(
                session,
                key="request-1",
                action_fingerprint="fingerprint-a",
            )
            raise RuntimeError("force rollback")

    with session_factory() as session:
        assert session.scalars(select(ExecutionClaim)).all() == []
        assert get_execution_claim(
            session,
            key="request-1",
            action_fingerprint="fingerprint-a",
        ) is None


def test_completed_claim_cannot_be_failed(session_factory):
    with session_factory.begin() as session:
        claim_execution(
            session,
            key="completed-cannot-fail",
            action_fingerprint="fingerprint-a",
        )
        complete_execution(
            session,
            key="completed-cannot-fail",
            action_fingerprint="fingerprint-a",
            result={"ok": True},
        )

    with session_factory.begin() as session:
        with pytest.raises(ExecutionClaimError):
            fail_execution(
                session,
                key="completed-cannot-fail",
                action_fingerprint="fingerprint-a",
                reason_code="late_failure",
            )

    with session_factory() as session:
        claim = get_execution_claim(
            session,
            key="completed-cannot-fail",
            action_fingerprint="fingerprint-a",
        )
        assert claim is not None
        assert claim.status == "COMPLETED"
        assert claim.result_json == '{"ok":true}'


def test_completed_claim_cannot_be_marked_unknown(session_factory):
    with session_factory.begin() as session:
        claim_execution(
            session,
            key="completed-cannot-be-unknown",
            action_fingerprint="fingerprint-a",
        )
        complete_execution(
            session,
            key="completed-cannot-be-unknown",
            action_fingerprint="fingerprint-a",
            result={"ok": True},
        )

    with session_factory.begin() as session:
        with pytest.raises(ExecutionClaimError):
            mark_execution_unknown(
                session,
                key="completed-cannot-be-unknown",
                action_fingerprint="fingerprint-a",
            )

    with session_factory() as session:
        claim = get_execution_claim(
            session,
            key="completed-cannot-be-unknown",
            action_fingerprint="fingerprint-a",
        )
        assert claim is not None
        assert claim.status == "COMPLETED"
