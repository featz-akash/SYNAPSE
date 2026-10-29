
"""Opt-in PostgreSQL concurrency tests for durable execution claims."""

from __future__ import annotations

import os
import threading
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from synapse.persistence.repositories.execution_claims import (
    ExecutionAlreadyInProgressError,
    ExecutionClaimConflictError,
    claim_execution,
)


@pytest.fixture
def postgres_engine():
    database_url = os.getenv("SYNAPSE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set SYNAPSE_TEST_DATABASE_URL to enable PostgreSQL concurrency tests."
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("These tests require PostgreSQL.")

    try:
        yield engine
    finally:
        engine.dispose()


def test_concurrent_claims_allow_only_one_winner(postgres_engine) -> None:
    """Only one transaction can claim a key, even under concurrent access."""
    key = f"claim-concurrency-{uuid4()}"
    fingerprint = "a" * 64

    first_claim_staged = threading.Event()
    allow_first_commit = threading.Event()
    second_attempt_started = threading.Event()

    first_errors: list[BaseException] = []
    second_outcomes: list[str] = []

    def first_transaction() -> None:
        try:
            with Session(postgres_engine) as session:
                with session.begin():
                    claim_execution(
                        session,
                        key=key,
                        action_fingerprint=fingerprint,
                    )
                    first_claim_staged.set()

                    if not allow_first_commit.wait(timeout=10):
                        raise TimeoutError(
                            "Timed out waiting to commit first claim."
                        )
        except BaseException as exc:
            first_errors.append(exc)
            first_claim_staged.set()

    def second_transaction() -> None:
        if not first_claim_staged.wait(timeout=10):
            second_outcomes.append("first_transaction_timeout")
            return

        try:
            with Session(postgres_engine) as session:
                with session.begin():
                    second_attempt_started.set()
                    claim_execution(
                        session,
                        key=key,
                        action_fingerprint=fingerprint,
                    )
                second_outcomes.append("unexpectedly_claimed")
        except ExecutionAlreadyInProgressError:
            second_outcomes.append("rejected_duplicate")
        except BaseException as exc:
            second_outcomes.append(
                f"unexpected_error:{type(exc).__name__}"
            )

    try:
        first_thread = threading.Thread(
            target=first_transaction,
            daemon=True,
        )
        second_thread = threading.Thread(
            target=second_transaction,
            daemon=True,
        )

        first_thread.start()
        assert first_claim_staged.wait(timeout=10), (
            "First transaction did not stage its claim."
        )

        second_thread.start()
        assert second_attempt_started.wait(timeout=10), (
            "Second transaction did not begin its attempt."
        )

        allow_first_commit.set()

        first_thread.join(timeout=15)
        second_thread.join(timeout=15)

        assert not first_thread.is_alive()
        assert not second_thread.is_alive()
        assert first_errors == []
        assert second_outcomes == ["rejected_duplicate"]

    finally:
        with Session(postgres_engine) as session:
            with session.begin():
                session.execute(
                    text("DELETE FROM execution_claims WHERE key = :key"),
                    {"key": key},
                )


def test_duplicate_claim_keeps_outer_transaction_usable(
    postgres_engine,
) -> None:
    """A duplicate claim must not poison the losing transaction."""
    key = f"claim-transaction-{uuid4()}"
    fingerprint = "b" * 64

    try:
        with Session(postgres_engine) as session:
            with session.begin():
                claim_execution(
                    session,
                    key=key,
                    action_fingerprint=fingerprint,
                )

        with Session(postgres_engine) as session:
            with session.begin():
                with pytest.raises(ExecutionAlreadyInProgressError):
                    claim_execution(
                        session,
                        key=key,
                        action_fingerprint=fingerprint,
                    )

                # Prove the outer transaction is still usable.
                session.execute(text("SELECT 1"))

        with Session(postgres_engine) as session:
            with session.begin():
                claim = session.get(
                    __import__(
                        "synapse.persistence.models.execution_claim",
                        fromlist=["ExecutionClaim"],
                    ).ExecutionClaim,
                    key,
                )
                assert claim is not None
                assert claim.status == "IN_PROGRESS"

    finally:
        with Session(postgres_engine) as session:
            with session.begin():
                session.execute(
                    text("DELETE FROM execution_claims WHERE key = :key"),
                    {"key": key},
                )


def test_claim_fingerprint_conflict_is_rejected(postgres_engine) -> None:
    """A key cannot be reused for a different action."""
    key = f"claim-fingerprint-{uuid4()}"

    try:
        with Session(postgres_engine) as session:
            with session.begin():
                claim_execution(
                    session,
                    key=key,
                    action_fingerprint="c" * 64,
                )

        with Session(postgres_engine) as session:
            with session.begin():
                with pytest.raises(ExecutionClaimConflictError):
                    claim_execution(
                        session,
                        key=key,
                        action_fingerprint="d" * 64,
                    )

                # The conflict is a domain-level rejection, not a database
                # integrity error, so the transaction should remain usable.
                session.execute(text("SELECT 1"))

    finally:
        with Session(postgres_engine) as session:
            with session.begin():
                session.execute(
                    text("DELETE FROM execution_claims WHERE key = :key"),
                    {"key": key},
                )
