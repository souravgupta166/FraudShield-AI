
from fastapi import FastAPI, HTTPException, Depends, Path
from sqlalchemy import create_engine, text, func, union
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from redis import Redis
from redis.exceptions import RedisError
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.data.database_models import (
    BitcoinBlock,
    BitcoinTransaction,
    BitcoinTransactionInput,
    BitcoinTransactionOutput,
    BitcoinIngestionRun,
)

from src.graph.bitcoin_transaction_graph import (
    build_bitcoin_transaction_graph,
    outpoint_node_id,
    transaction_node_id,
)
from src.risk.transaction_features import extract_transaction_features
from src.risk.sanctions_screening import screen_bitcoin_address
from src.risk.risk_indicators import (
    RiskThresholds,
    evaluate_transaction_indicators,
)
from src.risk.graph_risk_indicators import (
    GraphRiskThresholds,
    evaluate_graph_indicators,
    get_address_transaction_count,
)


# ==================================================
# 1. APPLICATION SETTINGS
# ==================================================

class Settings(BaseSettings):
    database_url: str
    redis_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()


# ==================================================
# 2. DATABASE CONNECTION
# ==================================================

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ==================================================
# 3. REDIS CONNECTION
# ==================================================

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True
)


# ==================================================
# 4. FASTAPI APPLICATION
# ==================================================

app = FastAPI(
    title="FraudShield AI",
    description=(
        "Bitcoin Blockchain Intelligence and "
        "Anti-Money Laundering Investigation API"
    ),
    version="0.1.0"
)


# ==================================================
# 5. ROOT ENDPOINT
# ==================================================

@app.get("/", tags=["System"])
def root():

    return {
        "application": "FraudShield AI",
        "version": "0.1.0",
        "status": "operational"
    }


# ==================================================
# 6. HEALTH ENDPOINT
# ==================================================

@app.get("/health", tags=["System"])
def health():

    return {
        "status": "healthy"
    }


# ==================================================
# 7. READINESS ENDPOINT
# ==================================================

@app.get("/ready", tags=["System"])
def readiness():

    try:

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        redis_client.ping()

        return {
            "status": "ready",
            "services": {
                "postgresql": "connected",
                "redis": "connected"
            }
        }

    except (SQLAlchemyError, RedisError):

        raise HTTPException(
            status_code=503,
            detail="One or more dependencies are unavailable"
        )


# ==================================================
# 8. APPLICATION INFORMATION
# ==================================================

@app.get("/api/v1/info", tags=["System"])
def application_info():

    return {
        "name": "FraudShield AI",
        "version": "0.1.0",
        "purpose": (
            "Bitcoin blockchain intelligence "
            "and AML investigation"
        ),
        "capabilities": [
            "Bitcoin transaction monitoring",
            "UTXO transaction analysis",
            "Address activity investigation",
            "Explainable risk indicators",
            "Blockchain investigation"
        ]
    }


# ==================================================
# 9. BITCOIN TRANSACTION LOOKUP
# ==================================================

@app.get(
    "/api/v1/bitcoin/transactions/{txid}",
    tags=["Bitcoin"],
    summary="Get Bitcoin transaction details"
)
def get_bitcoin_transaction(

    txid: str = Path(
        ...,
        pattern="^[a-fA-F0-9]{64}$",
        description="64-character Bitcoin transaction ID"
    ),

    db: Session = Depends(get_db)

):

    normalized_txid = txid.lower()

    transaction = db.get(
        BitcoinTransaction,
        normalized_txid
    )

    if transaction is None:

        raise HTTPException(
            status_code=404,
            detail="Bitcoin transaction not found"
        )

    inputs = (
        db.query(BitcoinTransactionInput)
        .filter(
            BitcoinTransactionInput.txid == normalized_txid
        )
        .order_by(
            BitcoinTransactionInput.input_index
        )
        .all()
    )

    outputs = (
        db.query(BitcoinTransactionOutput)
        .filter(
            BitcoinTransactionOutput.txid == normalized_txid
        )
        .order_by(
            BitcoinTransactionOutput.output_index
        )
        .all()
    )

    block = None

    if transaction.block_hash:

        block_record = db.get(
            BitcoinBlock,
            transaction.block_hash
        )

        if block_record:

            block = {
                "hash": block_record.block_hash,
                "height": block_record.height,
                "time": block_record.block_time.isoformat(),
                "transaction_count": block_record.tx_count,
                "is_canonical": block_record.is_canonical
            }

    fee_sats = transaction.fee_sats

    known_input_total = sum(
        item.prevout_value_sats
        for item in inputs
        if item.prevout_value_sats is not None
    )

    total_output = sum(
        item.value_sats
        for item in outputs
    )

    return {

        "transaction": {
            "txid": transaction.txid,
            "wtxid": transaction.wtxid,
            "version": transaction.version,
            "locktime": transaction.locktime,
            "size_bytes": transaction.size,
            "weight": transaction.weight,
            "fee_sats": fee_sats,
            "fee_btc": (
                f"{fee_sats / 100_000_000:.8f}"
                if fee_sats is not None else None
            ),
            "status": transaction.status,
            "first_seen_at": transaction.first_seen_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat()
        },

        "block": block,

        "inputs": [
            {
                "input_index": item.input_index,
                "previous_txid": item.previous_txid,
                "previous_output_index": item.previous_output_index,
                "prevout_value_sats": item.prevout_value_sats,
                "prevout_value_btc": (
                    f"{item.prevout_value_sats / 100_000_000:.8f}"
                    if item.prevout_value_sats is not None
                    else None
                ),
                "prevout_address": item.prevout_address,
                "sequence": item.sequence,
                "is_coinbase": item.is_coinbase,
                "script_sig_hex": item.script_sig_hex,
                "witness_data": item.witness_data
            }
            for item in inputs
        ],

        "outputs": [
            {
                "output_index": item.output_index,
                "value_sats": item.value_sats,
                "value_btc": f"{item.value_sats / 100_000_000:.8f}",
                "address": item.address,
                "script_type": item.script_type,
                "script_pubkey_hex": item.script_pubkey_hex
            }
            for item in outputs
        ],

        "summary": {
            "input_count": len(inputs),
            "output_count": len(outputs),
            "known_input_total_sats": known_input_total,
            "total_output_sats": total_output,
            "fee_sats": fee_sats,
            "accounting_complete": all(
                item.is_coinbase
                or item.prevout_value_sats is not None
                for item in inputs
            )
        }
    }



# ==================================================
# 9A. BITCOIN TRANSACTION INVESTIGATION
# ==================================================

@app.get(
    "/api/v1/bitcoin/transactions/{txid}/investigation",
    tags=["Bitcoin"],
    summary="Investigate a Bitcoin transaction",
    description=(
        "Combine transaction details, explainable risk indicators "
        "and observed UTXO graph relationships."
    ),
)
def get_bitcoin_transaction_investigation(
    txid: str = Path(
        ...,
        pattern="^[a-fA-F0-9]{64}$",
        description="64-character Bitcoin transaction ID",
    ),
    db: Session = Depends(get_db),
):
    normalized_txid = txid.lower()

    # Reuse the existing transaction endpoint's response.
    transaction_record = get_bitcoin_transaction(normalized_txid, db)

    transaction = db.get(BitcoinTransaction, normalized_txid)

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Bitcoin transaction not found",
        )

    inputs = (
        db.query(BitcoinTransactionInput)
        .filter(BitcoinTransactionInput.txid == normalized_txid)
        .order_by(BitcoinTransactionInput.input_index)
        .all()
    )

    outputs = (
        db.query(BitcoinTransactionOutput)
        .filter(BitcoinTransactionOutput.txid == normalized_txid)
        .order_by(BitcoinTransactionOutput.output_index)
        .all()
    )

    # --------------------------------------------------
    # 1. Transaction-level explainable indicators
    # --------------------------------------------------

    features = extract_transaction_features(
        transaction,
        inputs,
        outputs,
    )

    transaction_findings = evaluate_transaction_indicators(
        features,
        RiskThresholds(
            high_input_count=10,
            high_output_count=10,
        ),
    )

    # --------------------------------------------------
    # 2. Build observed UTXO graph
    # --------------------------------------------------

    graph = build_bitcoin_transaction_graph(db)
    tx_node = transaction_node_id(normalized_txid)

    input_outpoints = set()
    output_outpoints = set()
    previous_transaction_ids = set()
    spending_transaction_ids = set()
    input_addresses = set()
    output_addresses = set()

    if tx_node in graph:

        input_outpoints = {
            node
            for node in graph.predecessors(tx_node)
            if graph.nodes[node].get("node_type") == "outpoint"
        }

        output_outpoints = {
            node
            for node in graph.successors(tx_node)
            if graph.nodes[node].get("node_type") == "outpoint"
        }

        for outpoint in input_outpoints:
            for node in graph.predecessors(outpoint):
                node_type = graph.nodes[node].get("node_type")

                if node_type == "transaction":
                    previous_transaction_ids.add(
                        graph.nodes[node].get("txid")
                    )

                elif node_type == "address":
                    input_addresses.add(
                        graph.nodes[node].get("address")
                    )

        for outpoint in output_outpoints:
            for node in graph.successors(outpoint):
                node_type = graph.nodes[node].get("node_type")

                if node_type == "transaction":
                    spending_transaction_ids.add(
                        graph.nodes[node].get("txid")
                    )

                elif node_type == "address":
                    output_addresses.add(
                        graph.nodes[node].get("address")
                    )

    previous_transaction_ids.discard(None)
    spending_transaction_ids.discard(None)
    input_addresses.discard(None)
    output_addresses.discard(None)

    spending_transaction_ids.discard(normalized_txid)
    connected_transaction_ids = sorted(
        previous_transaction_ids | spending_transaction_ids
    )

    external_input_count = sum(
        1
        for node in input_outpoints
        if graph.nodes[node].get("source_transaction_observed") is False
    )

    # --------------------------------------------------
    # 3. Address activity evidence
    # --------------------------------------------------

    address_activity = []

    for address in sorted(input_addresses | output_addresses):
        observed_count = get_address_transaction_count(
            graph,
            address,
        )

        address_findings = evaluate_graph_indicators(
            graph,
            thresholds=GraphRiskThresholds(),
            address_filter=address,
        )

        address_activity.append(
            {
                "address": address,
                "observed_transaction_count": observed_count,
                "findings": address_findings,
            }
        )

    # --------------------------------------------------
    # 4. Screen observed transaction addresses against OFAC
    # --------------------------------------------------

    address_roles = {}

    for address in input_addresses:
        address_roles.setdefault(address, set()).add("input")

    for address in output_addresses:
        address_roles.setdefault(address, set()).add("output")

    sanctions_results = []

    for address in sorted(address_roles):
        screening_result = screen_bitcoin_address(db, address)

        sanctions_results.append(
            {
                "address": address,
                "transaction_roles": sorted(address_roles[address]),
                "screening": screening_result,
            }
        )

    matched_address_count = sum(
        1
        for item in sanctions_results
        if item["screening"]["is_sanctioned_address_match"]
    )

    # --------------------------------------------------
    # 5. Investigation response
    # --------------------------------------------------

    return {
        "network": "bitcoin",
        "transaction_record": transaction_record,
        "features": features,
        "transaction_findings": transaction_findings,
        "graph_context": {
            "dataset_scope": graph.graph.get("dataset_scope"),
            "block_height_filter": graph.graph.get("block_height_filter"),
            "stored_transaction_count": graph.graph.get(
                "transaction_count", 0
            ),
            "transaction_node_found": tx_node in graph,
            "input_outpoint_count": len(input_outpoints),
            "output_outpoint_count": len(output_outpoints),
            "external_input_outpoint_count": external_input_count,
            "known_previous_transaction_count": len(
                previous_transaction_ids
            ),
            "known_spending_transaction_count": len(
                spending_transaction_ids
            ),
            "known_previous_transaction_ids": sorted(
                previous_transaction_ids
            )[:20],
            "known_spending_transaction_ids": sorted(
                spending_transaction_ids
            )[:20],
            "connected_transaction_ids": connected_transaction_ids[:20],
            "connected_transaction_ids_truncated": (
                len(connected_transaction_ids) > 20
            ),
            "input_addresses": sorted(input_addresses),
            "output_addresses": sorted(output_addresses),
        },
        "address_activity": address_activity,
        "address_sanctions_screening": {
            "screened_address_count": len(sanctions_results),
            "matched_address_count": matched_address_count,
            "results": sanctions_results,
            "screening_note": (
                "Only addresses observed in the stored transaction graph "
                "are screened. A no-match result means the address was not "
                "found in the active OFAC snapshot; it does not establish "
                "that the address or transaction is safe."
            ),
        },
        "investigation_note": (
            "This investigation uses only transactions and UTXO "
            "relationships stored in FraudShield. Missing graph records "
            "do not establish that an output or transaction does not "
            "exist on the Bitcoin network. Risk indicators are explainable "
            "signals, not proof of fraud, illicit activity, identity "
            "or common ownership."
        ),
    }


# ==================================================
# 10. BITCOIN ADDRESS INTELLIGENCE
# ==================================================

@app.get(
    "/api/v1/bitcoin/addresses/{address}/summary",
    tags=["Bitcoin"],
    summary="Get Bitcoin address activity summary",
    description=(
        "Summarise incoming and outgoing activity "
        "observed in the FraudShield database."
    )
)
def get_bitcoin_address_summary(

    address: str = Path(
        ...,
        min_length=14,
        max_length=90,
        pattern="^[a-zA-Z0-9]+$",
        description="Bitcoin address"
    ),

    db: Session = Depends(get_db)

):

    # --------------------------------------------------
    # A. INCOMING ACTIVITY
    # --------------------------------------------------

    received_stats = (
        db.query(
            func.count(
                func.distinct(BitcoinTransactionOutput.txid)
            ),
            func.coalesce(
                func.sum(BitcoinTransactionOutput.value_sats),
                0
            ),
            func.min(BitcoinTransaction.first_seen_at),
            func.max(BitcoinTransaction.first_seen_at)
        )
        .join(
            BitcoinTransaction,
            BitcoinTransaction.txid
            == BitcoinTransactionOutput.txid
        )
        .filter(
            BitcoinTransactionOutput.address == address
        )
        .one()
    )

    received_transaction_count = int(received_stats[0])
    total_received_sats = int(received_stats[1])

    # --------------------------------------------------
    # B. OUTGOING ACTIVITY
    # --------------------------------------------------

    spent_stats = (
        db.query(
            func.count(
                func.distinct(BitcoinTransactionInput.txid)
            ),
            func.coalesce(
                func.sum(
                    BitcoinTransactionInput.prevout_value_sats
                ),
                0
            ),
            func.min(BitcoinTransaction.first_seen_at),
            func.max(BitcoinTransaction.first_seen_at)
        )
        .join(
            BitcoinTransaction,
            BitcoinTransaction.txid
            == BitcoinTransactionInput.txid
        )
        .filter(
            BitcoinTransactionInput.prevout_address == address
        )
        .one()
    )

    spent_transaction_count = int(spent_stats[0])
    total_spent_known_sats = int(spent_stats[1])

    unknown_spent_values = (
        db.query(BitcoinTransactionInput)
        .filter(
            BitcoinTransactionInput.prevout_address == address,
            BitcoinTransactionInput.prevout_value_sats.is_(None)
        )
        .count()
    )

    # --------------------------------------------------
    # C. DISTINCT TRANSACTION ACTIVITY
    # --------------------------------------------------

    activity_ids = (
        db.query(
            BitcoinTransactionOutput.txid.label("txid")
        )
        .filter(
            BitcoinTransactionOutput.address == address
        )
        .union(
            db.query(
                BitcoinTransactionInput.txid.label("txid")
            )
            .filter(
                BitcoinTransactionInput.prevout_address == address
            )
        )
        .subquery()
    )

    total_transactions = (
        db.query(func.count())
        .select_from(activity_ids)
        .scalar()
    )

    total_transactions = int(total_transactions or 0)

    if total_transactions == 0:

        raise HTTPException(
            status_code=404,
            detail=(
                "No stored blockchain activity found "
                "for this Bitcoin address"
            )
        )

    # --------------------------------------------------
    # D. FIRST AND LAST OBSERVED ACTIVITY
    # --------------------------------------------------

    first_observed = [
        value
        for value in (received_stats[2], spent_stats[2])
        if value is not None
    ]

    last_observed = [
        value
        for value in (received_stats[3], spent_stats[3])
        if value is not None
    ]

    first_activity = min(first_observed)
    last_activity = max(last_observed)

    # --------------------------------------------------
    # E. RECENT RELATED TRANSACTIONS
    # --------------------------------------------------

    recent_transactions = (
        db.query(BitcoinTransaction)
        .join(
            activity_ids,
            activity_ids.c.txid == BitcoinTransaction.txid
        )
        .order_by(
            BitcoinTransaction.first_seen_at.desc()
        )
        .limit(20)
        .all()
    )

    recent_txids = [
        transaction.txid
        for transaction in recent_transactions
    ]

    # Aggregate received values for recent transactions.

    recent_received = (
        db.query(
            BitcoinTransactionOutput.txid,
            func.sum(
                BitcoinTransactionOutput.value_sats
            )
        )
        .filter(
            BitcoinTransactionOutput.address == address,
            BitcoinTransactionOutput.txid.in_(recent_txids)
        )
        .group_by(
            BitcoinTransactionOutput.txid
        )
        .all()
    )

    received_by_txid = {
        txid: int(value)
        for txid, value in recent_received
    }

    # Aggregate known spent values for recent transactions.

    recent_spent = (
        db.query(
            BitcoinTransactionInput.txid,
            func.sum(
                BitcoinTransactionInput.prevout_value_sats
            )
        )
        .filter(
            BitcoinTransactionInput.prevout_address == address,
            BitcoinTransactionInput.prevout_value_sats.isnot(None),
            BitcoinTransactionInput.txid.in_(recent_txids)
        )
        .group_by(
            BitcoinTransactionInput.txid
        )
        .all()
    )

    spent_by_txid = {
        txid: int(value)
        for txid, value in recent_spent
    }

    recent_activity = []

    for transaction in recent_transactions:

        received = received_by_txid.get(transaction.txid, 0)
        spent = spent_by_txid.get(transaction.txid, 0)

        if received > 0 and spent > 0:
            direction = "both"
        elif received > 0:
            direction = "incoming"
        elif spent > 0:
            direction = "outgoing"
        else:
            direction = "activity"

        recent_activity.append({

            "txid": transaction.txid,

            "status": transaction.status,

            "direction": direction,

            "received_sats": received,

            "spent_known_sats": spent,

            "first_seen_at": (
                transaction.first_seen_at.isoformat()
            )
        })

    # --------------------------------------------------
    # F. FINAL RESPONSE
    # --------------------------------------------------

    return {

        "address": address,

        "network": "bitcoin",

        "data_scope": (
            "Activity observed in the FraudShield database; "
            "not necessarily the address's complete history."
        ),

        "activity_summary": {

            "total_transactions": total_transactions,

            "incoming_transactions": received_transaction_count,

            "outgoing_transactions": spent_transaction_count,

            "total_received_sats": total_received_sats,

            "total_received_btc": (
                f"{total_received_sats / 100_000_000:.8f}"
            ),

            "total_spent_known_sats": total_spent_known_sats,

            "total_spent_known_btc": (
                f"{total_spent_known_sats / 100_000_000:.8f}"
            ),

            "unknown_spent_input_values": unknown_spent_values,

            "spent_value_complete": unknown_spent_values == 0
        },

        "activity_period": {

            "first_observed_at": first_activity.isoformat(),

            "last_observed_at": last_activity.isoformat()
        },

        "recent_transactions": recent_activity,

        "investigation_note": (
            "Activity indicators describe observed on-chain records. "
            "They do not establish the identity or intent of an address owner."
        )
    }


# ==================================================
# 11. BITCOIN ADDRESS GRAPH RISK
# ==================================================

@app.get(
    "/api/v1/bitcoin/addresses/{address}/graph-risk",
    tags=["Bitcoin"],
    summary="Get graph-based Bitcoin address risk indicators",
    description=(
        "Evaluate observed UTXO graph activity for one Bitcoin address. "
        "Findings are investigation indicators, not proof of illicit activity."
    ),
)
def get_bitcoin_address_graph_risk(
    address: str = Path(
        ...,
        min_length=14,
        max_length=90,
        pattern="^[a-zA-Z0-9]+$",
        description="Bitcoin address",
    ),
    db: Session = Depends(get_db),
):
    graph = build_bitcoin_transaction_graph(db)

    observed_transaction_count = get_address_transaction_count(
        graph,
        address,
    )

    findings = evaluate_graph_indicators(
        graph,
        thresholds=GraphRiskThresholds(),
        address_filter=address,
    )

    return {
        "address": address,
        "network": "bitcoin",
        "observed_transaction_count": observed_transaction_count,
        "graph_scope": {
            "dataset_scope": graph.graph.get(
                "dataset_scope",
                "unspecified",
            ),
            "block_height_filter": graph.graph.get(
                "block_height_filter"
            ),
            "stored_transaction_count": graph.graph.get(
                "transaction_count",
                0,
            ),
            "graph_address_count": graph.graph.get(
                "address_count",
                0,
            ),
        },
        "findings": findings,
        "investigation_note": (
            "This analysis covers only transactions and UTXO relationships "
            "stored in FraudShield. An address with no findings is not "
            "necessarily low-risk. High activity is not proof of fraud, "
            "illicit activity, identity or common ownership."
        ),
    }



# ==================================================
# 12. BITCOIN ADDRESS SANCTIONS SCREENING
# ==================================================

@app.get(
    "/api/v1/bitcoin/addresses/{address}/sanctions-screening",
    tags=["Bitcoin"],
    summary="Screen a Bitcoin address against the active OFAC snapshot",
    description=(
        "Perform exact, case-sensitive Bitcoin address matching against "
        "the active OFAC sanctions dataset. A match is a screening result, "
        "not proof of ownership or illicit activity."
    ),
)
def get_bitcoin_address_sanctions_screening(
    address: str = Path(
        ...,
        min_length=14,
        max_length=90,
        pattern="^[a-zA-Z0-9]+$",
        description="Bitcoin address",
    ),
    db: Session = Depends(get_db),
):
    try:
        return screen_bitcoin_address(db, address)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


# ==================================================
# BITCOIN INGESTION MONITOR
# ==================================================

@app.get(
    "/api/v1/bitcoin/ingestion/monitor",
    tags=["Bitcoin"],
    summary="Bitcoin ingestion monitoring",
    description=(
        "Database-backed ingestion statistics, stored blockchain data, "
        "data freshness and recent ingestion runs."
    ),
)
def get_bitcoin_ingestion_monitor(
    db: Session = Depends(get_db),
):
    try:
        status_rows = (
            db.query(
                BitcoinIngestionRun.status,
                func.count(BitcoinIngestionRun.run_id),
            )
            .group_by(BitcoinIngestionRun.status)
            .all()
        )

        run_counts = {
            "completed": 0,
            "running": 0,
            "failed": 0,
        }

        for status, count in status_rows:
            run_counts[status] = count

        run_totals = (
            db.query(
                func.coalesce(
                    func.sum(BitcoinIngestionRun.blocks_processed), 0
                ),
                func.coalesce(
                    func.sum(BitcoinIngestionRun.transactions_processed), 0
                ),
            )
            .one()
        )

        total_runs = sum(run_counts.values())

        latest_run = (
            db.query(BitcoinIngestionRun)
            .order_by(BitcoinIngestionRun.started_at.desc())
            .first()
        )

        recent_runs = (
            db.query(BitcoinIngestionRun)
            .order_by(BitcoinIngestionRun.started_at.desc())
            .limit(10)
            .all()
        )

        canonical_block_count = (
            db.query(func.count(BitcoinBlock.block_hash))
            .filter(BitcoinBlock.is_canonical.is_(True))
            .scalar()
        )

        latest_block = (
            db.query(BitcoinBlock)
            .filter(BitcoinBlock.is_canonical.is_(True))
            .order_by(BitcoinBlock.height.desc())
            .first()
        )

        transaction_status_rows = (
            db.query(
                BitcoinTransaction.status,
                func.count(BitcoinTransaction.txid),
            )
            .group_by(BitcoinTransaction.status)
            .all()
        )

        transaction_counts = {
            "confirmed": 0,
            "mempool": 0,
            "orphaned": 0,
        }

        for status, count in transaction_status_rows:
            transaction_counts[status] = count

        total_stored_transactions = sum(transaction_counts.values())

        return {
            "status": (
                "degraded" if run_counts["failed"] > 0 else "operational"
            ),
            "ingestion_runs": {
                "total": total_runs,
                "completed": run_counts["completed"],
                "running": run_counts["running"],
                "failed": run_counts["failed"],
                "blocks_processed": int(run_totals[0]),
                "transactions_processed": int(run_totals[1]),
            },
            "blockchain_data": {
                "canonical_blocks_stored": int(canonical_block_count or 0),
                "latest_block_height": (
                    latest_block.height if latest_block else None
                ),
                "latest_block_hash": (
                    latest_block.block_hash if latest_block else None
                ),
                "total_stored_transactions": total_stored_transactions,
                "transactions_by_status": transaction_counts,
            },
            "latest_ingestion": (
                {
                    "source": latest_run.source,
                    "status": latest_run.status,
                    "started_at": latest_run.started_at.isoformat(),
                    "finished_at": (
                        latest_run.finished_at.isoformat()
                        if latest_run.finished_at else None
                    ),
                    "blocks_processed": latest_run.blocks_processed,
                    "transactions_processed": (
                        latest_run.transactions_processed
                    ),
                    "error_message": latest_run.error_message,
                }
                if latest_run else None
            ),
            "recent_runs": [
                {
                    "run_id": str(run.run_id),
                    "source": run.source,
                    "status": run.status,
                    "started_at": run.started_at.isoformat(),
                    "finished_at": (
                        run.finished_at.isoformat()
                        if run.finished_at else None
                    ),
                    "blocks_processed": run.blocks_processed,
                    "transactions_processed": run.transactions_processed,
                    "error_message": run.error_message,
                }
                for run in recent_runs
            ],
            "monitoring_note": (
                "Ingestion totals are aggregated from run records. "
                "Canonical block and transaction totals are queried "
                "directly from stored blockchain data. These metrics "
                "describe the locally collected dataset, not the complete "
                "Bitcoin network."
            ),
        }

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve Bitcoin ingestion statistics.",
        ) from exc
