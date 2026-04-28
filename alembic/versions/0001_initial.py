"""create payments and outbox_events tables

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-15 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────
    currency_enum = postgresql.ENUM(
        "RUB", "USD", "EUR", name="currency_enum", create_type=False
    )
    payment_status_enum = postgresql.ENUM(
        "pending", "succeeded", "failed", name="payment_status_enum", create_type=False
    )
    outbox_status_enum = postgresql.ENUM(
        "pending", "published", "failed", name="outbox_status_enum", create_type=False
    )

    currency_enum.create(op.get_bind(), checkfirst=True)
    payment_status_enum.create(op.get_bind(), checkfirst=True)
    outbox_status_enum.create(op.get_bind(), checkfirst=True)

    # ── payments ──────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "currency",
            sa.Enum("RUB", "USD", "EUR", name="currency_enum"),
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("webhook_url", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "succeeded", "failed", name="payment_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_payments_idempotency_key", "payments", ["idempotency_key"], unique=True
    )
    op.create_index(
        "ix_payments_status_created_at", "payments", ["status", "created_at"]
    )

    # ── outbox_events ─────────────────────────────────────────────────────────
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(26), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("routing_key", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "published", "failed", name="outbox_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Partial index: only index pending events (most frequent query)
    op.execute(
        """
        CREATE INDEX ix_outbox_status_created_at
        ON outbox_events (status, created_at)
        WHERE status = 'pending'
        """
    )


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("payments")

    op.execute("DROP TYPE IF EXISTS outbox_status_enum")
    op.execute("DROP TYPE IF EXISTS payment_status_enum")
    op.execute("DROP TYPE IF EXISTS currency_enum")
