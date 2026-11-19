import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class BitcoinBlock(Base):
    __tablename__ = "bitcoin_blocks"

    block_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    height: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    previous_block_hash: Mapped[str | None] = mapped_column(String(64))
    block_time: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_canonical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    observed_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ingestion_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'partial'")
    )
    next_transaction_index: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    ingested_transaction_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_ingested_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True)
    )
    ingestion_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("height >= 0", name="ck_bitcoin_blocks_height"),
        CheckConstraint("tx_count >= 0", name="ck_bitcoin_blocks_tx_count"),
        CheckConstraint(
            "ingestion_status IN "
            "('discovered', 'processing', 'partial', 'completed', 'failed')",
            name="ck_bitcoin_blocks_ingestion_status",
        ),
        CheckConstraint(
            "next_transaction_index >= 0 AND ingested_transaction_count >= 0",
            name="ck_bitcoin_blocks_ingestion_counts",
        ),
        Index("ix_bitcoin_blocks_canonical_height", "is_canonical", "height"),
    )


class BitcoinTransaction(Base):
    __tablename__ = "bitcoin_transactions"

    txid: Mapped[str] = mapped_column(String(64), primary_key=True)
    wtxid: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    locktime: Mapped[int] = mapped_column(BigInteger, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_sats: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'mempool'")
    )
    block_hash: Mapped[str | None] = mapped_column(
        ForeignKey("bitcoin_blocks.block_hash", ondelete="SET NULL")
    )
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    first_seen_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('mempool', 'confirmed', 'orphaned')",
            name="ck_bitcoin_transactions_status",
        ),
        CheckConstraint("size > 0", name="ck_bitcoin_transactions_size"),
        CheckConstraint("weight > 0", name="ck_bitcoin_transactions_weight"),
        CheckConstraint(
            "fee_sats IS NULL OR fee_sats >= 0",
            name="ck_bitcoin_transactions_fee",
        ),
        Index("ix_bitcoin_transactions_block_hash", "block_hash"),
        Index("ix_bitcoin_transactions_status", "status"),
    )


class BitcoinTransactionInput(Base):
    __tablename__ = "bitcoin_transaction_inputs"

    txid: Mapped[str] = mapped_column(
        ForeignKey("bitcoin_transactions.txid", ondelete="CASCADE"),
        primary_key=True,
    )
    input_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    previous_txid: Mapped[str | None] = mapped_column(String(64))
    previous_output_index: Mapped[int | None] = mapped_column(Integer)
    sequence: Mapped[int | None] = mapped_column(BigInteger)
    is_coinbase: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    script_sig_hex: Mapped[str | None] = mapped_column(Text)
    witness_data: Mapped[list | None] = mapped_column(JSONB)
    prevout_value_sats: Mapped[int | None] = mapped_column(BigInteger)
    prevout_script_pubkey_hex: Mapped[str | None] = mapped_column(Text)
    prevout_address: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("input_index >= 0", name="ck_bitcoin_inputs_index"),
        CheckConstraint(
            "prevout_value_sats IS NULL OR prevout_value_sats >= 0",
            name="ck_bitcoin_inputs_prevout_value",
        ),
        CheckConstraint(
            "(previous_txid IS NULL AND previous_output_index IS NULL) "
            "OR (previous_txid IS NOT NULL AND previous_output_index IS NOT NULL)",
            name="ck_bitcoin_inputs_previous_outpoint",
        ),
        Index("ix_bitcoin_inputs_previous_txid", "previous_txid"),
        Index("ix_bitcoin_inputs_prevout_address", "prevout_address"),
    )


class BitcoinTransactionOutput(Base):
    __tablename__ = "bitcoin_transaction_outputs"

    txid: Mapped[str] = mapped_column(
        ForeignKey("bitcoin_transactions.txid", ondelete="CASCADE"),
        primary_key=True,
    )
    output_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    script_pubkey_hex: Mapped[str] = mapped_column(Text, nullable=False)
    script_type: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("output_index >= 0", name="ck_bitcoin_outputs_index"),
        CheckConstraint("value_sats >= 0", name="ck_bitcoin_outputs_value"),
        Index("ix_bitcoin_outputs_address", "address"),
    )


class BitcoinIngestionRun(Base):
    __tablename__ = "bitcoin_ingestion_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    blocks_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    transactions_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_bitcoin_ingestion_runs_status",
        ),
        CheckConstraint(
            "blocks_processed >= 0 AND transactions_processed >= 0",
            name="ck_bitcoin_ingestion_runs_counts",
        ),
    )


class SanctionsSource(Base):
    __tablename__ = "sanctions_sources"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(100))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    downloaded_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    imported_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    record_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        CheckConstraint("record_count >= 0", name="ck_sanctions_sources_record_count"),
    )


class SanctionedCryptoAddress(Base):
    __tablename__ = "sanctioned_crypto_addresses"

    address_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sanctions_sources.source_id", ondelete="CASCADE"),
        nullable=False,
    )
    blockchain: Mapped[str] = mapped_column(String(30), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_name: Mapped[str] = mapped_column(Text, nullable=False)
    sanctions_program: Mapped[str | None] = mapped_column(String(255))
    source_record_id: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_record: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    first_seen_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "blockchain",
            "source_record_id",
            name="uq_sanctioned_address_source_chain_record",
        ),
        CheckConstraint(
            "length(address) > 0",
            name="ck_sanctioned_crypto_addresses_nonempty",
        ),
        Index(
            "ix_sanctioned_crypto_addresses_chain_address",
            "blockchain",
            "address",
        ),
        Index("ix_sanctioned_crypto_addresses_source_id", "source_id"),
        Index("ix_sanctioned_crypto_addresses_entity_id", "entity_id"),
    )
