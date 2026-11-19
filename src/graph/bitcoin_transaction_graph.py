
from __future__ import annotations

import networkx as nx

from sqlalchemy.orm import Session

from src.data.database_models import (
    BitcoinBlock,
    BitcoinTransaction,
    BitcoinTransactionInput,
    BitcoinTransactionOutput,
)


def transaction_node_id(txid: str) -> str:
    """Return a unique graph identifier for a Bitcoin transaction."""
    return f"tx:{txid}"


def outpoint_node_id(txid: str, output_index: int) -> str:
    """Return a unique identifier for a Bitcoin UTXO outpoint."""
    return f"outpoint:{txid}:{output_index}"


def address_node_id(address: str) -> str:
    """Return a unique identifier for an observed Bitcoin address."""
    return f"address:{address}"


def build_bitcoin_transaction_graph(
    session: Session,
    block_height: int | None = None,
) -> nx.MultiDiGraph:
    """
    Build an observed Bitcoin UTXO graph from PostgreSQL records.

    Parameters
    ----------
    session:
        Active SQLAlchemy database session.

    block_height:
        Optional Bitcoin block height. When supplied, only transactions
        confirmed in that block are included. When omitted, all stored
        transactions are included.

    Graph node types
    ----------------
    transaction:
        An observed Bitcoin transaction.

    outpoint:
        A specific transaction output identified by (txid, output_index).

    address:
        An address associated with an observed output script.

    Graph relationships
    -------------------
    transaction -> outpoint:
        A transaction creates an output.

    outpoint -> transaction:
        A transaction spends a previous output.

    outpoint -> address:
        An output script is associated with an address.

    address -> outpoint:
        A previous output script was associated with an address.

    Important limitations
    ---------------------
    - An address does not establish the identity or ownership of a person.
    - External outpoints may reference transactions not stored locally.
    - The graph represents observed records, not the complete Bitcoin network.
    - No direct address-to-address payment relationship is inferred.
    """

    # ---------------------------------------------------------
    # 1. Initialise graph
    # ---------------------------------------------------------

    graph = nx.MultiDiGraph(
        name="FraudShield Bitcoin UTXO Graph",
        network="bitcoin",
        graph_semantics="observed_utxo_relationships",
        block_height_filter=block_height,
    )

    # ---------------------------------------------------------
    # 2. Retrieve transactions
    # ---------------------------------------------------------

    transaction_query = session.query(BitcoinTransaction)

    if block_height is not None:

        matching_block_hashes = (
            session.query(BitcoinBlock.block_hash)
            .filter(BitcoinBlock.height == block_height)
        )

        transaction_query = transaction_query.filter(
            BitcoinTransaction.block_hash.in_(
                matching_block_hashes
            )
        )

    transactions = transaction_query.all()

    transaction_ids = [
        transaction.txid
        for transaction in transactions
    ]

    # ---------------------------------------------------------
    # 3. Retrieve associated inputs and outputs
    # ---------------------------------------------------------

    if transaction_ids:

        inputs = (
            session.query(BitcoinTransactionInput)
            .filter(
                BitcoinTransactionInput.txid.in_(transaction_ids)
            )
            .all()
        )

        outputs = (
            session.query(BitcoinTransactionOutput)
            .filter(
                BitcoinTransactionOutput.txid.in_(transaction_ids)
            )
            .all()
        )

    else:
        inputs = []
        outputs = []

    # ---------------------------------------------------------
    # 4. Add transaction nodes
    # ---------------------------------------------------------

    for transaction in transactions:

        tx_node = transaction_node_id(transaction.txid)

        graph.add_node(
            tx_node,
            node_type="transaction",
            txid=transaction.txid,
            status=transaction.status,
            block_hash=transaction.block_hash,
            fee_sats=transaction.fee_sats,
            size_bytes=transaction.size,
            weight=transaction.weight,
        )

    # ---------------------------------------------------------
    # 5. Add output and address nodes
    # ---------------------------------------------------------

    for output in outputs:

        tx_node = transaction_node_id(output.txid)

        outpoint_node = outpoint_node_id(
            output.txid,
            output.output_index,
        )

        # Add UTXO/outpoint node.
        graph.add_node(
            outpoint_node,
            node_type="outpoint",
            txid=output.txid,
            output_index=output.output_index,
            value_sats=output.value_sats,
            script_type=output.script_type,
            address_observed=output.address is not None,
            source_transaction_observed=True,
        )

        # Transaction creates this output.
        graph.add_edge(
            tx_node,
            outpoint_node,
            relationship="creates_output",
            value_sats=output.value_sats,
            output_index=output.output_index,
        )

        # Associate output script with observed address.
        if output.address:

            address_node = address_node_id(output.address)

            graph.add_node(
                address_node,
                node_type="address",
                address=output.address,
            )

            graph.add_edge(
                outpoint_node,
                address_node,
                relationship="output_script_associated_with_address",
                value_sats=output.value_sats,
            )

    # ---------------------------------------------------------
    # 6. Add input spending relationships
    # ---------------------------------------------------------

    for transaction_input in inputs:

        if transaction_input.is_coinbase:
            continue

        spending_tx_node = transaction_node_id(
            transaction_input.txid
        )

        previous_txid = transaction_input.previous_txid

        previous_index = (
            transaction_input.previous_output_index
        )

        if previous_txid is None or previous_index is None:
            continue

        previous_outpoint = outpoint_node_id(
            previous_txid,
            previous_index,
        )

        # Previous output might not exist in our local database.
        if previous_outpoint not in graph:

            graph.add_node(
                previous_outpoint,
                node_type="outpoint",
                txid=previous_txid,
                output_index=previous_index,
                value_sats=transaction_input.prevout_value_sats,
                script_type=None,
                address_observed=(
                    transaction_input.prevout_address is not None
                ),
                source_transaction_observed=False,
            )

        # Previous output is consumed by the spending transaction.
        graph.add_edge(
            previous_outpoint,
            spending_tx_node,
            relationship="spent_by",
            input_index=transaction_input.input_index,
            value_sats=transaction_input.prevout_value_sats,
        )

        # Associate previous output script with its observed address.
        if transaction_input.prevout_address:

            address_node = address_node_id(
                transaction_input.prevout_address
            )

            graph.add_node(
                address_node,
                node_type="address",
                address=transaction_input.prevout_address,
            )

            graph.add_edge(
                address_node,
                previous_outpoint,
                relationship=(
                    "previous_output_script_associated_with_address"
                ),
                value_sats=transaction_input.prevout_value_sats,
            )

    # ---------------------------------------------------------
    # 7. Calculate graph statistics
    # ---------------------------------------------------------

    node_types = {
        "transaction": 0,
        "outpoint": 0,
        "address": 0,
    }

    for _, data in graph.nodes(data=True):

        node_type = data.get("node_type")

        if node_type in node_types:
            node_types[node_type] += 1

    relationship_counts = {
        "creates_output": 0,
        "spent_by": 0,
        "output_script_associated_with_address": 0,
        "previous_output_script_associated_with_address": 0,
    }

    for _, _, data in graph.edges(data=True):

        relationship = data.get("relationship")

        if relationship in relationship_counts:
            relationship_counts[relationship] += 1

    external_outpoints = sum(
        1
        for _, data in graph.nodes(data=True)
        if (
            data.get("node_type") == "outpoint"
            and data.get("source_transaction_observed") is False
        )
    )

    # ---------------------------------------------------------
    # 8. Attach metadata
    # ---------------------------------------------------------

    graph.graph.update(
        {
            "transaction_count": node_types["transaction"],
            "outpoint_count": node_types["outpoint"],
            "address_count": node_types["address"],
            "external_outpoint_count": external_outpoints,
            "input_relationship_count": relationship_counts["spent_by"],
            "output_relationship_count": relationship_counts[
                "creates_output"
            ],
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
            "relationship_counts": relationship_counts,
            "dataset_scope": (
                "block"
                if block_height is not None
                else "all_stored_transactions"
            ),
        }
    )

    return graph
