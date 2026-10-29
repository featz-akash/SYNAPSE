
from sqlalchemy import create_engine, inspect

from synapse.persistence.models import AuditChainHead, Base


def test_audit_chain_head_table_is_registered() -> None:
    assert AuditChainHead.__tablename__ == "audit_chain_heads"


def test_chain_head_has_sequence_and_hash() -> None:
    columns = Base.metadata.tables["audit_chain_heads"].columns

    assert "sequence_number" in columns
    assert "last_hash" in columns
    assert "updated_at" in columns


def test_chain_head_table_can_be_created_in_isolated_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        assert "audit_chain_heads" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
