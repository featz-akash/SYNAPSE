
from datetime import UTC, datetime

import pytest

from synapse.execution.approvals import (
    ApprovalRegistry,
    ApprovalRequiredError,
)


def test_action_requires_explicit_approval():
    registry = ApprovalRegistry()

    with pytest.raises(ApprovalRequiredError):
        registry.require_approved("action-1")


def test_approval_is_bound_to_action_id():
    registry = ApprovalRegistry()

    registry.approve(
        action_id="action-1",
        approver_id="human-reviewer",
    )

    assert registry.is_approved("action-1")
    assert not registry.is_approved("action-2")


def test_approval_records_approver_and_timestamp():
    registry = ApprovalRegistry()
    timestamp = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

    record = registry.approve(
        action_id="action-1",
        approver_id="human-reviewer",
        approved_at=timestamp,
    )

    assert record.approver_id == "human-reviewer"
    assert record.approved_at == timestamp


def test_approval_can_be_revoked():
    registry = ApprovalRegistry()
    registry.approve(
        action_id="action-1",
        approver_id="human-reviewer",
    )

    assert registry.revoke("action-1") is True
    assert registry.revoke("action-1") is False
    assert not registry.is_approved("action-1")


def test_naive_approval_timestamp_is_rejected():
    registry = ApprovalRegistry()

    with pytest.raises(ValueError, match="timezone-aware"):
        registry.approve(
            action_id="action-1",
            approver_id="human-reviewer",
            approved_at=datetime(2026, 10, 27, 12, 0),
        )

def test_revocation_prevents_new_approval_claims():
    registry = ApprovalRegistry()
    registry.approve(
        action_id="action-1",
        approver_id="human-reviewer",
    )

    with registry.hold_approval("action-1") as record:
        assert record.action_id == "action-1"

        # The current claim remains valid, but revocation removes
        # approval for any subsequent claim.
        assert registry.revoke("action-1") is True

        with pytest.raises(ApprovalRequiredError):
            with registry.hold_approval("action-1"):
                pytest.fail("Revoked approval must not be claimable")

    assert not registry.is_approved("action-1")
