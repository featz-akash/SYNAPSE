
"""Create durable execution claims for idempotent tool execution.

Revision ID: 0004_durable_execution_claims
Revises: 0003_durable_audit
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_durable_execution_claims"
down_revision = "0003_durable_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_claims",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("action_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'COMPLETED', 'FAILED', 'UNKNOWN')",
            name="ck_execution_claims_status",
        ),
    )

    op.create_index(
        "ix_execution_claims_status",
        "execution_claims",
        ["status"],
    )
    op.create_index(
        "ix_execution_claims_updated_at",
        "execution_claims",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_execution_claims_updated_at",
        table_name="execution_claims",
    )
    op.drop_index(
        "ix_execution_claims_status",
        table_name="execution_claims",
    )
    op.drop_table("execution_claims")
