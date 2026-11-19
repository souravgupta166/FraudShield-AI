from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "FraudShield AI"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_application_info():
    response = client.get("/api/v1/info")

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "FraudShield AI"

    expected_capabilities = [
        "Bitcoin transaction monitoring",
        "UTXO transaction analysis",
        "Address activity investigation",
        "Explainable risk indicators",
        "Blockchain investigation",
    ]

    for capability in expected_capabilities:
        assert capability in data["capabilities"]


def test_readiness_endpoint():
    response = client.get("/ready")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"
    assert data["services"]["postgresql"] == "connected"
    assert data["services"]["redis"] == "connected"


def test_bitcoin_address_graph_risk_with_finding(monkeypatch):
    import api.main as api_module
    from types import SimpleNamespace

    address = "bc1q1234567890abcdefghijk1234567890"

    fake_graph = SimpleNamespace(
        graph={
            "dataset_scope": "all_stored_transactions",
            "block_height_filter": None,
            "transaction_count": 12,
            "address_count": 8,
        }
    )

    monkeypatch.setattr(
        api_module,
        "build_bitcoin_transaction_graph",
        lambda db: fake_graph,
    )
    monkeypatch.setattr(
        api_module,
        "get_address_transaction_count",
        lambda graph, requested_address: 6,
    )
    monkeypatch.setattr(
        api_module,
        "evaluate_graph_indicators",
        lambda graph, thresholds, address_filter: [
            {
                "indicator": "high_observed_address_activity",
                "severity": "informational",
                "address": address,
                "observed_transaction_count": 6,
            }
        ],
    )

    response = client.get(
        f"/api/v1/bitcoin/addresses/{address}/graph-risk"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["address"] == address
    assert data["network"] == "bitcoin"
    assert data["observed_transaction_count"] == 6
    assert data["graph_scope"]["dataset_scope"] == "all_stored_transactions"
    assert data["graph_scope"]["stored_transaction_count"] == 12
    assert len(data["findings"]) == 1
    assert data["findings"][0]["indicator"] == (
        "high_observed_address_activity"
    )


def test_bitcoin_address_graph_risk_without_findings(monkeypatch):
    import api.main as api_module
    from types import SimpleNamespace

    address = "bc1q1234567890abcdefghijk1234567890"

    fake_graph = SimpleNamespace(
        graph={
            "dataset_scope": "all_stored_transactions",
            "block_height_filter": None,
            "transaction_count": 12,
            "address_count": 8,
        }
    )

    monkeypatch.setattr(
        api_module,
        "build_bitcoin_transaction_graph",
        lambda db: fake_graph,
    )
    monkeypatch.setattr(
        api_module,
        "get_address_transaction_count",
        lambda graph, requested_address: 2,
    )
    monkeypatch.setattr(
        api_module,
        "evaluate_graph_indicators",
        lambda graph, thresholds, address_filter: [],
    )

    response = client.get(
        f"/api/v1/bitcoin/addresses/{address}/graph-risk"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["observed_transaction_count"] == 2
    assert data["findings"] == []
    assert "not necessarily low-risk" in data["investigation_note"]


def test_bitcoin_address_graph_risk_rejects_invalid_address():
    response = client.get(
        "/api/v1/bitcoin/addresses/invalid-address!/graph-risk"
    )

    assert response.status_code == 422


def test_bitcoin_transaction_investigation_success(monkeypatch):
    import networkx as nx
    import api.main as api_module
    from types import SimpleNamespace

    txid = "a" * 64
    previous_txid = "b" * 64
    spending_txid = "c" * 64

    input_address = "bc1qinputaddress123456789"
    output_address = "bc1qoutputaddress123456789"

    target_node = f"tx:{txid}"
    previous_node = f"tx:{previous_txid}"
    spending_node = f"tx:{spending_txid}"
    input_outpoint = "outpoint:previous:0"
    output_outpoint = f"outpoint:{txid}:0"

    graph = nx.MultiDiGraph()

    graph.add_node(
        target_node,
        node_type="transaction",
        txid=txid,
    )
    graph.add_node(
        previous_node,
        node_type="transaction",
        txid=previous_txid,
    )
    graph.add_node(
        spending_node,
        node_type="transaction",
        txid=spending_txid,
    )
    graph.add_node(
        input_outpoint,
        node_type="outpoint",
        source_transaction_observed=True,
    )
    graph.add_node(
        output_outpoint,
        node_type="outpoint",
        source_transaction_observed=True,
    )
    graph.add_node(
        f"address:{input_address}",
        node_type="address",
        address=input_address,
    )
    graph.add_node(
        f"address:{output_address}",
        node_type="address",
        address=output_address,
    )

    graph.add_edge(previous_node, input_outpoint)
    graph.add_edge(f"address:{input_address}", input_outpoint)
    graph.add_edge(input_outpoint, target_node)

    graph.add_edge(target_node, output_outpoint)
    graph.add_edge(output_outpoint, f"address:{output_address}")
    graph.add_edge(output_outpoint, spending_node)

    graph.graph.update(
        {
            "dataset_scope": "all_stored_transactions",
            "block_height_filter": None,
            "transaction_count": 3,
            "address_count": 2,
        }
    )

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return []

    class FakeDatabase:
        def get(self, model, key):
            return SimpleNamespace(txid=txid)

        def query(self, model):
            return FakeQuery()

        def close(self):
            pass

    monkeypatch.setattr(
        api_module,
        "get_bitcoin_transaction",
        lambda requested_txid, db: {
            "transaction": {"txid": requested_txid},
            "inputs": [],
            "outputs": [],
            "summary": {},
        },
    )
    monkeypatch.setattr(
        api_module,
        "build_bitcoin_transaction_graph",
        lambda db: graph,
    )
    monkeypatch.setattr(
        api_module,
        "transaction_node_id",
        lambda requested_txid: f"tx:{requested_txid}",
    )
    monkeypatch.setattr(
        api_module,
        "extract_transaction_features",
        lambda transaction, inputs, outputs: {
            "txid": txid,
            "input_count": 1,
            "output_count": 1,
            "fee_reconciliation_valid": True,
        },
    )
    monkeypatch.setattr(
        api_module,
        "evaluate_transaction_indicators",
        lambda features, thresholds: [
            {
                "indicator": "large_input_consolidation",
                "severity": "informational",
            }
        ],
    )
    monkeypatch.setattr(
        api_module,
        "get_address_transaction_count",
        lambda graph, address: 2,
    )
    monkeypatch.setattr(
        api_module,
        "evaluate_graph_indicators",
        lambda graph, thresholds, address_filter: [],
    )

    def fake_screen_bitcoin_address(db, requested_address):
        is_match = requested_address == input_address

        return {
            "blockchain": "bitcoin",
            "address": requested_address,
            "match_status": "exact_match" if is_match else "no_match",
            "is_sanctioned_address_match": is_match,
            "match_count": 1 if is_match else 0,
            "matches": [{"entity_id": "test-entity"}] if is_match else [],
            "investigation_note": "Mocked OFAC screening result.",
        }

    monkeypatch.setattr(
        api_module,
        "screen_bitcoin_address",
        fake_screen_bitcoin_address,
    )

    monkeypatch.setattr(
        api_module,
        "SessionLocal",
        lambda: FakeDatabase(),
    )

    response = client.get(
        f"/api/v1/bitcoin/transactions/{txid}/investigation"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["network"] == "bitcoin"
    assert data["transaction_record"]["transaction"]["txid"] == txid

    assert data["features"]["fee_reconciliation_valid"] is True

    assert data["transaction_findings"][0]["indicator"] == (
        "large_input_consolidation"
    )

    context = data["graph_context"]

    assert context["transaction_node_found"] is True
    assert context["known_previous_transaction_ids"] == [previous_txid]
    assert context["known_spending_transaction_ids"] == [spending_txid]
    assert context["input_addresses"] == [input_address]
    assert context["output_addresses"] == [output_address]

    assert len(data["address_activity"]) == 2

    screening = data["address_sanctions_screening"]

    assert screening["screened_address_count"] == 2
    assert screening["matched_address_count"] == 1

    screening_by_address = {
        item["address"]: item
        for item in screening["results"]
    }

    assert screening_by_address[input_address]["transaction_roles"] == ["input"]
    assert screening_by_address[input_address]["screening"]["match_status"] == "exact_match"

    assert screening_by_address[output_address]["transaction_roles"] == ["output"]
    assert screening_by_address[output_address]["screening"]["match_status"] == "no_match"

    assert "does not establish" in screening["screening_note"]
    assert "not proof of fraud" in data["investigation_note"]
