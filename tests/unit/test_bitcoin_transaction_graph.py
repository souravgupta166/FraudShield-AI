from types import SimpleNamespace

from src.data.database_models import (
    BitcoinTransaction,
    BitcoinTransactionInput,
    BitcoinTransactionOutput,
)
from src.graph.bitcoin_transaction_graph import (
    address_node_id,
    build_bitcoin_transaction_graph,
    outpoint_node_id,
    transaction_node_id,
)


class FakeQuery:
    def __init__(self, records):
        self.records = records

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.records


class FakeSession:
    def __init__(self, transactions=None, inputs=None, outputs=None):
        self.records = {
            BitcoinTransaction: transactions or [],
            BitcoinTransactionInput: inputs or [],
            BitcoinTransactionOutput: outputs or [],
        }

    def query(self, model):
        return FakeQuery(self.records[model])


def make_transaction(txid, block_hash="block-1"):
    return SimpleNamespace(
        txid=txid,
        status="confirmed",
        block_hash=block_hash,
        fee_sats=100,
        size=200,
        weight=800,
    )


def make_input(
    txid,
    input_index=0,
    previous_txid="previous-tx",
    previous_output_index=0,
    is_coinbase=False,
    prevout_value_sats=5000,
    prevout_address="bc1qexample",
):
    return SimpleNamespace(
        txid=txid,
        input_index=input_index,
        previous_txid=previous_txid,
        previous_output_index=previous_output_index,
        is_coinbase=is_coinbase,
        prevout_value_sats=prevout_value_sats,
        prevout_address=prevout_address,
    )


def make_output(
    txid,
    output_index=0,
    value_sats=4900,
    address="bc1qdestination",
):
    return SimpleNamespace(
        txid=txid,
        output_index=output_index,
        value_sats=value_sats,
        script_type="v0_p2wpkh",
        address=address,
    )


def test_graph_creates_transaction_outpoint_and_address_nodes():
    transaction = make_transaction("tx-1")
    output = make_output("tx-1")

    graph = build_bitcoin_transaction_graph(
        FakeSession(
            transactions=[transaction],
            outputs=[output],
        )
    )

    tx_node = transaction_node_id("tx-1")
    output_node = outpoint_node_id("tx-1", 0)
    address_node = address_node_id("bc1qdestination")

    assert graph.nodes[tx_node]["node_type"] == "transaction"
    assert graph.nodes[output_node]["node_type"] == "outpoint"
    assert graph.nodes[address_node]["node_type"] == "address"

    assert graph.has_edge(tx_node, output_node)
    assert graph.has_edge(output_node, address_node)


def test_graph_records_external_previous_outpoint():
    transaction = make_transaction("tx-2")
    transaction_input = make_input(
        txid="tx-2",
        previous_txid="external-tx",
        previous_output_index=3,
    )

    graph = build_bitcoin_transaction_graph(
        FakeSession(
            transactions=[transaction],
            inputs=[transaction_input],
        )
    )

    previous_outpoint = outpoint_node_id("external-tx", 3)
    spending_transaction = transaction_node_id("tx-2")

    assert previous_outpoint in graph
    assert graph.nodes[previous_outpoint]["source_transaction_observed"] is False
    assert graph.nodes[previous_outpoint]["value_sats"] == 5000

    assert graph.has_edge(previous_outpoint, spending_transaction)


def test_graph_links_locally_observed_previous_output():
    producer = make_transaction("producer-tx")
    spender = make_transaction("spender-tx")

    produced_output = make_output(
        txid="producer-tx",
        output_index=2,
        value_sats=8000,
        address="bc1qproducer",
    )

    spending_input = make_input(
        txid="spender-tx",
        previous_txid="producer-tx",
        previous_output_index=2,
        prevout_value_sats=8000,
        prevout_address="bc1qproducer",
    )

    graph = build_bitcoin_transaction_graph(
        FakeSession(
            transactions=[producer, spender],
            inputs=[spending_input],
            outputs=[produced_output],
        )
    )

    previous_outpoint = outpoint_node_id("producer-tx", 2)
    spending_transaction = transaction_node_id("spender-tx")

    assert graph.nodes[previous_outpoint]["source_transaction_observed"] is True
    assert graph.nodes[previous_outpoint]["value_sats"] == 8000
    assert graph.has_edge(previous_outpoint, spending_transaction)


def test_graph_skips_coinbase_spending_relationship():
    transaction = make_transaction("coinbase-tx")
    coinbase_input = make_input(
        txid="coinbase-tx",
        previous_txid=None,
        previous_output_index=None,
        is_coinbase=True,
        prevout_value_sats=None,
        prevout_address=None,
    )

    graph = build_bitcoin_transaction_graph(
        FakeSession(
            transactions=[transaction],
            inputs=[coinbase_input],
        )
    )

    assert graph.number_of_nodes() == 1
    assert graph.number_of_edges() == 0


def test_graph_supports_outputs_without_addresses():
    transaction = make_transaction("tx-no-address")
    output = make_output(
        txid="tx-no-address",
        address=None,
    )

    graph = build_bitcoin_transaction_graph(
        FakeSession(
            transactions=[transaction],
            outputs=[output],
        )
    )

    output_node = outpoint_node_id("tx-no-address", 0)

    assert output_node in graph
    assert graph.nodes[output_node]["address_observed"] is False
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1


def test_graph_statistics_match_graph_contents():
    transaction = make_transaction("tx-stats")
    output = make_output("tx-stats")
    transaction_input = make_input(
        txid="tx-stats",
        previous_txid="external-tx",
        previous_output_index=1,
    )

    graph = build_bitcoin_transaction_graph(
        FakeSession(
            transactions=[transaction],
            inputs=[transaction_input],
            outputs=[output],
        )
    )

    assert graph.graph["transaction_count"] == 1
    assert graph.graph["outpoint_count"] == 2
    assert graph.graph["address_count"] == 2
    assert graph.graph["external_outpoint_count"] == 1
    assert graph.graph["input_relationship_count"] == 1
    assert graph.graph["output_relationship_count"] == 1
    assert graph.graph["total_nodes"] == graph.number_of_nodes()
    assert graph.graph["total_edges"] == graph.number_of_edges()
    assert graph.graph["dataset_scope"] == "all_stored_transactions"


def test_empty_dataset_returns_empty_graph():
    graph = build_bitcoin_transaction_graph(FakeSession())

    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
    assert graph.graph["transaction_count"] == 0
    assert graph.graph["outpoint_count"] == 0
    assert graph.graph["address_count"] == 0
    assert graph.graph["external_outpoint_count"] == 0
    assert graph.graph["dataset_scope"] == "all_stored_transactions"
