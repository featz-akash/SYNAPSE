
from sqlalchemy import create_engine, inspect

from synapse.persistence.models import AuditRecord, Base


def test_audit_events_table_is_registered() -> None:
    assert "audit_events" in Base.metadata.tables


def test_audit_model_contains_integrity_fields() -> None:
    columns = Base.metadata.tables["audit_events"].columns

    assert "sequence_number" in columns
    assert "previous_hash" in columns
    assert "event_hash" in columns
    assert "canonical_event" in columns


def test_audit_model_has_no_cascading_domain_foreign_keys() -> None:
    table = Base.metadata.tables["audit_events"]

    assert len(table.foreign_keys) == 0


def test_audit_model_can_create_in_isolated_sqlite_database() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        assert "audit_events" in inspector.get_table_names()
    finally:
        engine.dispose()


def test_audit_record_uses_expected_table_name() -> None:
    assert AuditRecord.__tablename__ == "audit_events"
