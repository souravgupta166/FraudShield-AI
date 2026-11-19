"""add Bitcoin block ingestion tracking

Revision ID: 7c4e91a2b6d0
Revises: 469512a39bbf
Create Date: 2026-11-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c4e91a2b6d0"
down_revision: Union[str, Sequence[str], None] = "469512a39bbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bitcoin_blocks",
        sa.Column(
            "ingestion_status",
            sa.String(length=20),
            server_default=sa.text("'partial'"),
            nullable=False,
        ),
    )
    op.add_column(
        "bitcoin_blocks",
        sa.Column(
            "next_transaction_index",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "bitcoin_blocks",
        sa.Column(
            "ingested_transaction_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "bitcoin_blocks",
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "bitcoin_blocks",
        sa.Column("ingestion_error", sa.Text(), nullable=True),
    )

    op.create_check_constraint(
        "ck_bitcoin_blocks_ingestion_status",
        "bitcoin_blocks",
        "ingestion_status IN "
        "('discovered', 'processing', 'partial', 'completed', 'failed')",
    )
    op.create_check_constraint(
        "ck_bitcoin_blocks_ingestion_counts",
        "bitcoin_blocks",
        "next_transaction_index >= 0 AND ingested_transaction_count >= 0",
    )

    op.execute("""
        UPDATE bitcoin_blocks AS b
        SET ingested_transaction_count = counts.stored_count,
            ingestion_status = CASE
                WHEN counts.stored_count >= b.tx_count THEN 'completed'
                ELSE 'partial'
            END
        FROM (
            SELECT b2.block_hash, COUNT(t.txid)::integer AS stored_count
            FROM bitcoin_blocks AS b2
            LEFT JOIN bitcoin_transactions AS t
                ON t.block_hash = b2.block_hash
            GROUP BY b2.block_hash
        ) AS counts
        WHERE b.block_hash = counts.block_hash
    """)


def downgrade() -> None:
    op.drop_constraint(
        "ck_bitcoin_blocks_ingestion_counts",
        "bitcoin_blocks",
        type_="check",
    )
    op.drop_constraint(
        "ck_bitcoin_blocks_ingestion_status",
        "bitcoin_blocks",
        type_="check",
    )
    op.drop_column("bitcoin_blocks", "ingestion_error")
    op.drop_column("bitcoin_blocks", "last_ingested_at")
    op.drop_column("bitcoin_blocks", "ingested_transaction_count")
    op.drop_column("bitcoin_blocks", "next_transaction_index")
    op.drop_column("bitcoin_blocks", "ingestion_status")
