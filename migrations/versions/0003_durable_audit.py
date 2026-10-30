
"""Create durable, hash-chained audit storage.

Revision ID: 0003_durable_audit
Revises: 0002_canonical_states
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_durable_audit"
down_revision = "0002_canonical_states"
branch_labels = None
depends_on = None

GENESIS_HASH = "0" * 64


def upgrade() -> None:
    op.create_table(
        "audit_chain_heads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "last_hash",
            sa.String(length=64),
            nullable=False,
            server_default=GENESIS_HASH,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "sequence_number >= 0",
            name="ck_audit_chain_heads_sequence_nonnegative",
        ),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column("objective_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("policy_version", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("canonical_event", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "sequence_number",
            name="uq_audit_events_sequence",
        ),
    )

    op.create_index(
        "ix_audit_events_action_id",
        "audit_events",
        ["action_id"],
    )
    op.create_index(
        "ix_audit_events_correlation_id",
        "audit_events",
        ["correlation_id"],
    )
    op.create_index(
        "ix_audit_events_occurred_at",
        "audit_events",
        ["occurred_at"],
    )

    # Initialize the single global chain head.
    op.bulk_insert(
        sa.table(
            "audit_chain_heads",
            sa.column("id", sa.Integer()),
            sa.column("sequence_number", sa.Integer()),
            sa.column("last_hash", sa.String(length=64)),
        ),
        [
            {
                "id": 1,
                "sequence_number": 0,
                "last_hash": GENESIS_HASH,
            }
        ],
    )


def downgrade() -> None:
    # Remove audit storage only. Never modify objectives or tasks here.
    op.drop_index(
        "ix_audit_events_occurred_at",
        table_name="audit_events",
    )
    op.drop_index(
        "ix_audit_events_correlation_id",
        table_name="audit_events",
    )
    op.drop_index(
        "ix_audit_events_action_id",
        table_name="audit_events",
    )
    op.drop_table("audit_events")
    op.drop_table("audit_chain_heads")
