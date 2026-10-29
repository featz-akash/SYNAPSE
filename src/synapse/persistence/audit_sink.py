
"""SQLAlchemy-backed durable audit sink for SYNAPSE."""

from __future__ import annotations

from collections.abc import Callable

from synapse.persistence.repositories.audit import append_audit_event
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork
from synapse.security.audit import AuditEvent


UnitOfWorkFactory = Callable[[], SqlAlchemyUnitOfWork]


class SqlAlchemyAuditSink:
    """Persist each audit event in its own database transaction.

    This sink guarantees that an event and its hash-chain-head update are
    committed or rolled back together.

    It does not make external tool execution atomic with the audit write.
    """

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def append(self, event: AuditEvent) -> None:
        """Append an event durably or raise if persistence fails."""
        with self._unit_of_work_factory() as uow:
            append_audit_event(uow.session, event)
