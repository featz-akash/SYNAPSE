
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from synapse.persistence.models import AuditChainHead, Base
from synapse.persistence.repositories.audit import (
    AuditIntegrityError,
    append_audit_event,
    verify_audit_chain,
)
from synapse.security.audit import AuditEvent, AuditOutcome


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    with factory.begin() as session:
        session.add(
            AuditChainHead(
                id=1,
                sequence_number=0,
                last_hash="0" * 64,
            )
        )

    yield factory
    engine.dispose()


def make_event(action_id: str = "action-1") -> AuditEvent:
    return AuditEvent(
        event_type="action.execution",
        outcome=AuditOutcome.COMMITTED,
        actor_id="test-actor",
        action_id=action_id,
        objective_id="objective-1",
        task_id="task-1",
        reason_code="executed",
        policy_version="v1",
        occurred_at=datetime(2026, 10, 28, tzinfo=UTC),
        correlation_id="correlation-1",
    )


def test_append_and_verify_audit_event(session_factory) -> None:
    with session_factory.begin() as session:
        record = append_audit_event(session, make_event())
        assert record.sequence_number == 1

    with session_factory() as session:
        assert verify_audit_chain(session)


def test_multiple_events_form_ordered_chain(session_factory) -> None:
    with session_factory.begin() as session:
        first = append_audit_event(session, make_event("action-1"))
        second = append_audit_event(session, make_event("action-2"))

        assert first.sequence_number == 1
        assert second.sequence_number == 2
        assert second.previous_hash == first.event_hash

    with session_factory() as session:
        assert verify_audit_chain(session)


def test_rollback_does_not_persist_event_or_advance_head(session_factory) -> None:
    with pytest.raises(RuntimeError, match="force rollback"):
        with session_factory.begin() as session:
            append_audit_event(session, make_event())
            raise RuntimeError("force rollback")

    with session_factory() as session:
        assert verify_audit_chain(session)
        head = session.get(AuditChainHead, 1)
        assert head is not None
        assert head.sequence_number == 0


def test_event_tampering_is_detected(session_factory) -> None:
    with session_factory.begin() as session:
        append_audit_event(session, make_event())

    with session_factory.begin() as session:
        record = session.query(
            __import__(
                "synapse.persistence.models.audit",
                fromlist=["AuditRecord"],
            ).AuditRecord
        ).one()
        record.reason_code = "tampered"

    with session_factory() as session:
        with pytest.raises(AuditIntegrityError):
            verify_audit_chain(session)

def test_verify_detects_occurred_at_column_tampering(
    session_factory,
) -> None:
    from datetime import UTC, datetime

    import pytest

    from synapse.persistence.models.audit import AuditRecord
    from synapse.persistence.repositories.audit import (
        AuditIntegrityError,
        append_audit_event,
        verify_audit_chain,
    )

    with session_factory() as session:
        with session.begin():
            append_audit_event(session, make_event())

    with session_factory() as session:
        with session.begin():
            record = session.query(AuditRecord).first()
            assert record is not None
            record.occurred_at = datetime(2020, 1, 1, tzinfo=UTC)

    with session_factory() as session:
        with pytest.raises(AuditIntegrityError, match="timestamp mismatch"):
            verify_audit_chain(session)