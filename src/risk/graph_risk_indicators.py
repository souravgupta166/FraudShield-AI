from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx


@dataclass(frozen=True)
class GraphRiskThresholds:
    """
    Configurable thresholds for graph-based investigation indicators.

    These thresholds identify activity patterns for review.
    They are not calibrated fraud thresholds.
    """

    high_address_transaction_count: int = 5

    def __post_init__(self) -> None:
        if (
            isinstance(self.high_address_transaction_count, bool)
            or not isinstance(self.high_address_transaction_count, int)
            or self.high_address_transaction_count < 2
        ):
            raise ValueError(
                "high_address_transaction_count must be an integer >= 2"
            )


def _transactions_associated_with_address(
    graph: nx.MultiDiGraph,
    address_node: str,
) -> set[str]:
    """
    Return distinct observed transaction IDs associated with an address.

    Traversal follows the existing UTXO graph relationships:
    address -> previous outpoint -> spending transaction
    outpoint -> address, with the outpoint's creating transaction.

    No direct address-to-address relationship is inferred.
    """

    associated_transactions: set[str] = set()

    # Address associations can point either into or out of an outpoint.
    adjacent_outpoints = (
        set(graph.predecessors(address_node))
        | set(graph.successors(address_node))
    )

    for outpoint in adjacent_outpoints:
        if graph.nodes[outpoint].get("node_type") != "outpoint":
            continue

        # Include the observed transaction that created this outpoint.
        for creator in graph.predecessors(outpoint):
            creator_data = graph.nodes[creator]

            if creator_data.get("node_type") == "transaction":
                txid = creator_data.get("txid")
                if isinstance(txid, str):
                    associated_transactions.add(txid)

        # Include observed transactions that spent this outpoint.
        for spender in graph.successors(outpoint):
            spender_data = graph.nodes[spender]

            if spender_data.get("node_type") == "transaction":
                txid = spender_data.get("txid")
                if isinstance(txid, str):
                    associated_transactions.add(txid)

    return associated_transactions


def get_address_transaction_count(
    graph: nx.MultiDiGraph,
    address: str,
) -> int:
    """Return the distinct observed transaction count for one address."""

    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("graph must be a NetworkX MultiDiGraph")

    if not isinstance(address, str) or not address.strip():
        raise ValueError("address must be a non-empty string")

    address_node = f"address:{address}"

    if address_node not in graph:
        return 0

    if graph.nodes[address_node].get("node_type") != "address":
        return 0

    return len(
        _transactions_associated_with_address(graph, address_node)
    )


def evaluate_graph_indicators(
    graph: nx.MultiDiGraph,
    thresholds: GraphRiskThresholds | None = None,
    address_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Identify high observed transaction activity around address nodes.

    Results describe only relationships represented in the supplied graph.
    They do not establish address ownership, identity or illicit activity.
    """

    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("graph must be a NetworkX MultiDiGraph")

    if address_filter is not None and (
        not isinstance(address_filter, str) or not address_filter.strip()
    ):
        raise ValueError("address_filter must be a non-empty string")

    thresholds = thresholds or GraphRiskThresholds()

    findings: list[dict[str, Any]] = []

    for node, data in graph.nodes(data=True):
        if data.get("node_type") != "address":
            continue

        address = data.get("address")

        if not isinstance(address, str) or not address:
            continue

        if address_filter is not None and address != address_filter:
            continue

        associated_transactions = (
            _transactions_associated_with_address(graph, node)
        )

        observed_count = len(associated_transactions)

        if observed_count < thresholds.high_address_transaction_count:
            continue

        findings.append(
            {
                "indicator_code": "high_observed_address_activity",
                "category": "graph_activity",
                "severity": "informational",
                "title": "High observed address activity",
                "description": (
                    "The address is associated with a relatively large "
                    "number of distinct transactions in the collected graph."
                ),
                "evidence": {
                    "address": address,
                    "distinct_observed_transaction_count": observed_count,
                    "threshold": (
                        thresholds.high_address_transaction_count
                    ),
                    "observed_transaction_ids": sorted(
                        associated_transactions
                    ),
                    "dataset_scope": graph.graph.get(
                        "dataset_scope",
                        "unspecified",
                    ),
                    "block_height_filter": graph.graph.get(
                        "block_height_filter"
                    ),
                },
                "caveat": (
                    "High address activity can reflect legitimate exchange, "
                    "custodial, payment-processing or wallet operations. "
                    "The graph covers only collected records and does not "
                    "establish address ownership or illicit activity."
                ),
            }
        )

    findings.sort(
        key=lambda finding: (
            -finding["evidence"]["distinct_observed_transaction_count"],
            finding["evidence"]["address"],
        )
    )

    return findings
