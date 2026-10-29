
import pytest

from synapse.execution.approvals import ApprovalRegistry
from synapse.execution.factory import create_audited_executor
from synapse.execution.idempotency import IdempotencyRegistry
from synapse.execution.permissions import PermissionChecker
from synapse.execution.tool_registry import ToolRegistry


class RecordingSink:
    def append(self, event) -> None:
        pass


def test_factory_requires_explicit_audit_sink():
    with pytest.raises(ValueError, match="durable audit sink is required"):
        create_audited_executor(
            registry=ToolRegistry(),
            audit_sink=None,
        )


def test_factory_constructs_executor_with_audit_sink():
    sink = RecordingSink()

    executor = create_audited_executor(
        registry=ToolRegistry(),
        audit_sink=sink,
        approvals=ApprovalRegistry(),
        idempotency=IdempotencyRegistry(),
        permission_checker=PermissionChecker(),
    )

    assert executor is not None
    assert executor._audit_sink is sink
