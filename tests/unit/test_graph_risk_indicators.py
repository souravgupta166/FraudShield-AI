import networkx as nx
import pytest

from src.risk.graph_risk_indicators import (
    GraphRiskThresholds,
    evaluate_graph_indicators,
)


def make_graph():
    graph = nx.MultiDiGraph(
        dataset_scope="all_stored_transactions",
        block_height_filter=None,
    )

    graph.add_node("address:bc1qshared", node_type="address", address="bc1qshared")

    # Transaction A creates an output associated with the address.
    graph.add_node("tx:a", node_type="transaction", txid="a")
    graph.add_node("outpoint:a:0", node_type="outpoint")
    graph.add_edge("tx:a", "outpoint:a:0")
    graph.add_edge("outpoint:a:0", "address:bc1qshared")

    # Transaction B spends an outpoint associated with the address.
    graph.add_node("tx:b", node_type="transaction", txid="b")
    graph.add_node("outpoint:external:0", node_type="outpoint")
    graph.add_edge("address:bc1qshared", "outpoint:external:0")
    graph.add_edge("outpoint:external:0", "tx:b")

    # Transaction C also spends an outpoint associated with the address.
    graph.add_node("tx:c", node_type="transaction", txid="c")
    graph.add_node("outpoint:external:1", node_type="outpoint")
    graph.add_edge("address:bc1qshared", "outpoint:external:1")
    graph.add_edge("outpoint:external:1", "tx:c")

    # A second address, with one observed transaction.
    graph.add_node("address:bc1qother", node_type="address", address="bc1qother")
    graph.add_node("tx:d", node_type="transaction", txid="d")
    graph.add_node("outpoint:d:0", node_type="outpoint")
    graph.add_edge("tx:d", "outpoint:d:0")
    graph.add_edge("outpoint:d:0", "address:bc1qother")

    return graph


def test_address_activity_counts_distinct_transactions():
    graph = make_graph()

    findings = evaluate_graph_indicators(
        graph,
        GraphRiskThresholds(high_address_transaction_count=3),
    )

    assert len(findings) == 1
    finding = findings[0]

    assert finding["indicator_code"] == "high_observed_address_activity"
    assert finding["evidence"]["address"] == "bc1qshared"
    assert finding["evidence"]["distinct_observed_transaction_count"] == 3
    assert finding["evidence"]["observed_transaction_ids"] == ["a", "b", "c"]


def test_address_below_threshold_is_not_flagged():
    graph = make_graph()

    findings = evaluate_graph_indicators(
        graph,
        GraphRiskThresholds(high_address_transaction_count=4),
    )

    assert findings == []


def test_transaction_is_not_counted_twice_for_same_address():
    graph = make_graph()

    # Add a second output from transaction A associated with the same address.
    graph.add_node("outpoint:a:1", node_type="outpoint")
    graph.add_edge("tx:a", "outpoint:a:1")
    graph.add_edge("outpoint:a:1", "address:bc1qshared")

    findings = evaluate_graph_indicators(
        graph,
        GraphRiskThresholds(high_address_transaction_count=3),
    )

    assert len(findings) == 1
    assert findings[0]["evidence"]["distinct_observed_transaction_count"] == 3


def test_finding_includes_dataset_scope_and_caveat():
    graph = make_graph()

    findings = evaluate_graph_indicators(
        graph,
        GraphRiskThresholds(high_address_transaction_count=2),
    )

    assert findings[0]["evidence"]["dataset_scope"] == "all_stored_transactions"
    assert "does not establish address ownership" in findings[0]["caveat"]


def test_empty_graph_returns_no_findings():
    assert evaluate_graph_indicators(nx.MultiDiGraph()) == []


def test_invalid_threshold_is_rejected():
    with pytest.raises(ValueError):
        GraphRiskThresholds(high_address_transaction_count=1)


def test_non_multidigraph_is_rejected():
    with pytest.raises(TypeError):
        evaluate_graph_indicators(nx.Graph())



def test_address_filter_returns_only_requested_address():
    graph = make_graph()

    findings = evaluate_graph_indicators(
        graph,
        GraphRiskThresholds(high_address_transaction_count=2),
        address_filter="bc1qshared",
    )

    assert len(findings) == 1
    assert findings[0]["evidence"]["address"] == "bc1qshared"


def test_address_filter_excludes_other_addresses():
    graph = make_graph()

    findings = evaluate_graph_indicators(
        graph,
        GraphRiskThresholds(high_address_transaction_count=2),
        address_filter="bc1qother",
    )

    assert findings == []


def test_unknown_address_filter_returns_no_findings():
    graph = make_graph()

    findings = evaluate_graph_indicators(
        graph,
        address_filter="bc1qunknown",
    )

    assert findings == []


@pytest.mark.parametrize("invalid_filter", ["", "   ", 123, True])
def test_invalid_address_filter_is_rejected(invalid_filter):
    graph = make_graph()

    with pytest.raises(ValueError):
        evaluate_graph_indicators(graph, address_filter=invalid_filter)
