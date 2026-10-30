
import pytest

from synapse.execution.idempotency import (
    IdempotencyConflictError,
    IdempotencyError,
    IdempotencyInProgressError,
    IdempotencyRegistry,
)


def test_completed_action_can_be_retrieved():
    registry = IdempotencyRegistry()

    assert registry.begin("request-1", "fingerprint-a") is True
    registry.complete("request-1", {"status": "ok"})

    record = registry.get_completed("request-1", "fingerprint-a")

    assert record is not None
    assert record.result == {"status": "ok"}
    assert registry.begin("request-1", "fingerprint-a") is False


def test_key_reuse_for_different_action_is_rejected():
    registry = IdempotencyRegistry()
    registry.begin("request-1", "fingerprint-a")
    registry.complete("request-1", "done")

    with pytest.raises(IdempotencyConflictError):
        registry.begin("request-1", "fingerprint-b")


def test_concurrent_duplicate_is_rejected():
    registry = IdempotencyRegistry()
    registry.begin("request-1", "fingerprint-a")

    with pytest.raises(IdempotencyInProgressError):
        registry.begin("request-1", "fingerprint-a")


def test_failed_action_can_be_retried():
    registry = IdempotencyRegistry()
    registry.begin("request-1", "fingerprint-a")
    registry.fail("request-1")

    assert registry.begin("request-1", "fingerprint-a") is True


def test_complete_requires_active_reservation():
    registry = IdempotencyRegistry()

    with pytest.raises(IdempotencyError):
        registry.complete("request-1", "result")


def test_cached_result_requires_matching_fingerprint():
    registry = IdempotencyRegistry()
    registry.begin("request-1", "fingerprint-a")
    registry.complete("request-1", "result")

    with pytest.raises(IdempotencyConflictError):
        registry.get_completed("request-1", "fingerprint-b")
