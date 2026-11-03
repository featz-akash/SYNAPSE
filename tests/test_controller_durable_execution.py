from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from synapse.cognition.controller.durable_execution import (
    DurableControllerExecutionService,
    action_fingerprint,
)
from synapse.cognition.controller.operation_service import ControllerOperationService
from synapse.persistence.models import Base
from synapse.persistence.models.execution_claim import ExecutionClaim
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork
from synapse.persistence.repositories.execution_claims import (
    ExecutionAlreadyInProgressError,
    ExecutionClaimConflictError,
)
from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.security.policy_engine import PolicyContext


@pytest.fixture
def factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield lambda: SqlAlchemyUnitOfWork(maker)
    finally:
        engine.dispose()


def action():
    obj = Objective(title="Durable operation", success_criteria=("done",))
    task = Task(objective_id=obj.id, title="execute")
    return ProposedAction(
        objective_id=obj.id,
        task_id=task.id,
        tool_name="read",
        kind=ActionKind.READ,
    )


def context():
    return PolicyContext(actor_id="actor-a", granted_permissions=frozenset({"actions:read"}))


def test_claimed_operation_executes_once_and_completes(factory):
    service = DurableControllerExecutionService(factory)
    result = service.execute(
        idempotency_key="idem-1",
        action=action(),
        context=context(),
        operation=lambda: {"success": True},
    )
    assert result.operation.executed
    with factory() as uow:
        claim = uow.session.get(ExecutionClaim, "idem-1")
        assert claim is not None and claim.status == "COMPLETED"
        assert claim.result_json == '{"allowed":true,"executed":true}'


def test_duplicate_in_progress_request_is_rejected(factory):
    act = action()
    fingerprint = action_fingerprint(act)
    with factory() as uow:
        from synapse.persistence.repositories.execution_claims import claim_execution
        claim_execution(uow.session, key="idem-2", action_fingerprint=fingerprint)

    with pytest.raises(ExecutionAlreadyInProgressError):
        DurableControllerExecutionService(factory).execute(
            idempotency_key="idem-2",
            action=act,
            context=context(),
            operation=Mock(),
        )


def test_same_key_different_action_is_rejected(factory):
    act1, act2 = action(), action()
    with factory() as uow:
        from synapse.persistence.repositories.execution_claims import claim_execution
        claim_execution(
            uow.session, key="idem-3", action_fingerprint=action_fingerprint(act1)
        )
    with pytest.raises(ExecutionClaimConflictError):
        DurableControllerExecutionService(factory).execute(
            idempotency_key="idem-3",
            action=act2,
            context=context(),
            operation=Mock(),
        )


def test_operation_exception_marks_claim_failed(factory):
    service = DurableControllerExecutionService(factory)
    with pytest.raises(ValueError):
        service.execute(
            idempotency_key="idem-4",
            action=action(),
            context=context(),
            operation=Mock(side_effect=ValueError("not persisted")),
        )
    with factory() as uow:
        claim = uow.session.get(ExecutionClaim, "idem-4")
        assert claim is not None and claim.status == "FAILED"
        assert claim.reason_code == "ValueError"
