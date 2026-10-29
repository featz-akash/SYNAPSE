from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine

from synapse.persistence.database import (
    DATABASE_URL_ENV,
    create_database_engine,
    create_session_factory,
    resolve_database_url,
)
from synapse.persistence.models import Base, ObjectiveRecord
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork

VALID_URL = "postgresql+psycopg://synapse:secret@localhost:5432/synapse_test"


def test_resolve_database_url_accepts_postgresql_url() -> None:
    assert resolve_database_url(VALID_URL) == VALID_URL


def test_resolve_database_url_reads_environment() -> None:
    assert resolve_database_url(environ={DATABASE_URL_ENV: VALID_URL}) == VALID_URL


@pytest.mark.parametrize("value", [None, "", "  "])
def test_resolve_database_url_requires_value(value: str | None) -> None:
    with pytest.raises(ValueError, match="database URL is required"):
        resolve_database_url(value, environ={})


def test_resolve_database_url_rejects_sqlite() -> None:
    with pytest.raises(ValueError, match="requires a PostgreSQL"):
        resolve_database_url("sqlite:///synapse.db")


def test_resolve_database_url_requires_database_name() -> None:
    with pytest.raises(ValueError, match="database name"):
        resolve_database_url("postgresql+psycopg://user:pass@localhost")


def test_resolve_database_url_requires_host() -> None:
    with pytest.raises(ValueError, match="specify a host"):
        resolve_database_url("postgresql+psycopg:///synapse")


def test_invalid_url_error_does_not_echo_credentials() -> None:
    secret_url = "not-a-url-with-secret"
    with pytest.raises(ValueError) as captured:
        resolve_database_url(secret_url)
    assert secret_url not in str(captured.value)


def test_create_engine_uses_validated_postgresql_url() -> None:
    sentinel_engine = MagicMock()
    with patch(
        "synapse.persistence.database.create_engine",
        return_value=sentinel_engine,
    ) as create_engine_mock:
        engine = create_database_engine(VALID_URL)

    assert engine is sentinel_engine
    create_engine_mock.assert_called_once_with(
        VALID_URL,
        echo=False,
        pool_pre_ping=True,
    )


def test_session_factory_is_bound_to_engine() -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        factory = create_session_factory(engine)
        session = factory()
        try:
            assert session.bind is engine
            assert session.autoflush is False
            assert session.expire_on_commit is False
        finally:
            session.close()
    finally:
        engine.dispose()


def test_base_metadata_registers_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "objectives",
        "tasks",
        "task_dependencies",
        "audit_events",
        "audit_chain_heads",
        "execution_claims",
    }


def test_uow_commits_on_success_and_closes_session() -> None:
    session = MagicMock()
    transaction = MagicMock()
    session.begin.return_value = transaction
    uow = SqlAlchemyUnitOfWork(lambda: session)

    with uow as active:
        assert active.session is session

    transaction.__exit__.assert_called_once_with(None, None, None)
    session.close.assert_called_once()


def test_uow_propagates_exception_and_closes_session() -> None:
    session = MagicMock()
    transaction = MagicMock()
    session.begin.return_value = transaction
    uow = SqlAlchemyUnitOfWork(lambda: session)
    error = RuntimeError("operation failed")

    with pytest.raises(RuntimeError, match="operation failed"):
        with uow:
            raise error

    transaction.__exit__.assert_called_once()
    args = transaction.__exit__.call_args.args
    assert args[0] is RuntimeError
    assert args[1] is error
    session.close.assert_called_once()


def test_uow_session_is_unavailable_outside_context() -> None:
    uow = SqlAlchemyUnitOfWork(lambda: MagicMock())
    with pytest.raises(RuntimeError, match="not active"):
        _ = uow.session


def test_uow_persists_changes_after_successful_transaction() -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        factory = create_session_factory(engine)
        uow = SqlAlchemyUnitOfWork(factory)

        with uow as active:
            active.session.add(
                ObjectiveRecord(
                    id="uow-commit-test",
                    title="Commit test",
                    description="",
                    success_criteria=["persist"],
                    state="draft",
                    revision=0,
                )
            )

        with factory() as session:
            saved = session.get(ObjectiveRecord, "uow-commit-test")
            assert saved is not None
            assert saved.title == "Commit test"
    finally:
        engine.dispose()


def test_uow_rolls_back_changes_after_exception() -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        factory = create_session_factory(engine)
        uow = SqlAlchemyUnitOfWork(factory)

        with pytest.raises(RuntimeError, match="force rollback"):
            with uow as active:
                active.session.add(
                    ObjectiveRecord(
                        id="uow-rollback-test",
                        title="Rollback test",
                        description="",
                        success_criteria=["must not persist"],
                        state="draft",
                        revision=0,
                    )
                )
                raise RuntimeError("force rollback")

        with factory() as session:
            saved = session.get(ObjectiveRecord, "uow-rollback-test")
            assert saved is None
    finally:
        engine.dispose()


def test_uow_closes_session_when_commit_fails() -> None:
    session = MagicMock()
    transaction = MagicMock()
    transaction.__exit__.side_effect = RuntimeError("commit failed")
    session.begin.return_value = transaction
    uow = SqlAlchemyUnitOfWork(lambda: session)

    with pytest.raises(RuntimeError, match="commit failed"):
        with uow:
            pass

    session.close.assert_called_once()

    # The UoW should release its internal state even after a failed exit.
    with pytest.raises(RuntimeError, match="not active"):
        _ = uow.session
