
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from synapse.persistence.audit_sink import SqlAlchemyAuditSink
from synapse.persistence.models import Base
from synapse.persistence.models.audit import AuditRecord
from synapse.persistence.models.audit_head import AuditChainHead
from synapse.persistence.repositories.audit import (
    GENESIS_HASH,
    AuditIntegrityError,
    verify_audit_chain,
)
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork
from synapse.security.audit import AuditEvent, AuditOutcome


@pytest.fixture
def audit_setup():
    # This database exists only for this test; it is not the application DB.
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory.begin() as session:
        session.add(
            AuditChainHead(
                id=1,
                sequence_number=0,
                last_hash=GENESIS_HASH,
            )
        )

    sink = SqlAlchemyAuditSink(
        lambda: SqlAlchemyUnitOfWork(factory)
    )

    try:
        yield factory, sink
    finally:
        engine.dispose()


def make_event() -> AuditEvent:
    return AuditEvent(
        event_type="action.execution",
        outcome=AuditOutcome.COMMITTED,
        actor_id="test-actor",
        action_id="action-1",
        objective_id="objective-1",
        task_id="task-1",
        reason_code="execution_succeeded",
        policy_version="test-policy-v1",
        occurred_at=datetime(2026, 10, 28, tzinfo=UTC),
        correlation_id="test-correlation",
    )


def test_sink_commits_event_and_chain_head(audit_setup):
    factory, sink = audit_setup

    sink.append(make_event())

    with factory() as session:
        records = session.scalars(
            select(AuditRecord).order_by(AuditRecord.sequence_number)
        ).all()
        head = session.get(AuditChainHead, 1)

        assert len(records) == 1
        assert records[0].sequence_number == 1
        assert records[0].outcome == AuditOutcome.COMMITTED.value
        assert head is not None
        assert head.sequence_number == 1
        assert head.last_hash == records[0].event_hash
        assert verify_audit_chain(session) is True


def test_sink_persists_multiple_events_in_order(audit_setup):
    factory, sink = audit_setup

    sink.append(make_event())
    sink.append(
        AuditEvent(
            event_type="action.execution",
            outcome=AuditOutcome.FAILED,
            actor_id="test-actor",
            action_id="action-2",
            objective_id="objective-1",
            task_id="task-1",
            reason_code="RuntimeError",
            policy_version="test-policy-v1",
            occurred_at=datetime(2026, 10, 28, 0, 1, tzinfo=UTC),
        )
    )

    with factory() as session:
        records = session.scalars(
            select(AuditRecord).order_by(AuditRecord.sequence_number)
        ).all()

        assert [record.sequence_number for record in records] == [1, 2]
        assert records[1].previous_hash == records[0].event_hash
        assert verify_audit_chain(session) is True


def test_sink_rolls_back_event_and_head_on_append_failure(
    audit_setup, monkeypatch
):
    factory, sink = audit_setup

    def fail_after_staging(session, event):
        from synapse.persistence.repositories.audit import append_audit_event

        append_audit_event(session, event)
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(
        "synapse.persistence.audit_sink.append_audit_event",
        fail_after_staging,
    )

    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        sink.append(make_event())

    with factory() as session:
        records = session.scalars(select(AuditRecord)).all()
        head = session.get(AuditChainHead, 1)

        assert records == []
        assert head is not None
        assert head.sequence_number == 0
        assert head.last_hash == GENESIS_HASH
        assert verify_audit_chain(session) is True
