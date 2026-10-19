"""Transaction boundary for a single SYNAPSE persistence operation."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Literal

from sqlalchemy.orm import Session, SessionTransaction

SessionFactory = Callable[[], Session]


class SqlAlchemyUnitOfWork:
    """Manage one session and one transaction for a bounded operation.

    The unit of work commits on a successful context exit and rolls back when
    the body raises. It always closes its session. It does not make external
    side effects atomic with database writes.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._transaction: SessionTransaction | None = None

    @property
    def session(self) -> Session:
        """Return the active session, rejecting use outside the context."""
        if self._session is None:
            raise RuntimeError("The unit-of-work session is not active.")
        return self._session

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        if self._session is not None:
            raise RuntimeError("This unit-of-work instance is already active.")

        session = self._session_factory()
        try:
            transaction = session.begin()
        except BaseException:
            session.close()
            raise

        self._session = session
        self._transaction = transaction
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,

    ) -> Literal[False]:

        session = self._session
        transaction = self._transaction
        if session is None or transaction is None:
            raise RuntimeError("The unit-of-work context is not active.")

        try:

            transaction.__exit__(exc_type, exc_value, traceback)
            return False

        finally:
            try:
                session.close()
            finally:
                self._session = None
                self._transaction = None
