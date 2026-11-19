import httpx
import pytest

from src.data.mempool_client import MempoolClient


VALID_BLOCK_HASH = "a" * 64


def mock_response(text: str) -> httpx.Response:
    request = httpx.Request(
        "GET",
        "https://mempool.space/api/block-height/976421",
    )
    return httpx.Response(
        200,
        text=text,
        request=request,
    )


def test_get_block_hash_at_height(monkeypatch):
    with MempoolClient() as client:
        monkeypatch.setattr(
            client,
            "_get",
            lambda path: mock_response(VALID_BLOCK_HASH),
        )

        result = client.get_block_hash_at_height(976421)

    assert result == VALID_BLOCK_HASH


@pytest.mark.parametrize("height", [-1, True, 1.5, "976421"])
def test_reject_invalid_block_height(height):
    with MempoolClient() as client:
        with pytest.raises(ValueError, match="block height"):
            client.get_block_hash_at_height(height)


def test_reject_invalid_hash_returned_by_api(monkeypatch):
    with MempoolClient() as client:
        monkeypatch.setattr(
            client,
            "_get",
            lambda path: mock_response("not-a-valid-block-hash"),
        )

        with pytest.raises(ValueError, match="invalid block hash"):
            client.get_block_hash_at_height(976421)


def test_block_height_lookup_uses_correct_api_endpoint(monkeypatch):
    requested_paths = []

    def fake_get(path):
        requested_paths.append(path)
        return mock_response(VALID_BLOCK_HASH)

    with MempoolClient() as client:
        monkeypatch.setattr(client, "_get", fake_get)
        client.get_block_hash_at_height(976421)

    assert requested_paths == ["/block-height/976421"]


def test_get_block_transactions_adds_verified_block_status(monkeypatch):
    txid = "b" * 64
    payload = [{
        "txid": txid,
        "version": 2,
        "locktime": 0,
        "size": 150,
        "weight": 600,
        "fee": 100,
        "vin": [{"is_coinbase": True}],
        "vout": [{"value": 5000000000}],
    }]
    requested_paths = []

    def fake_get(path):
        requested_paths.append(path)
        request = httpx.Request(
            "GET",
            "https://mempool.space/api" + path,
        )
        return httpx.Response(200, json=payload, request=request)

    with MempoolClient() as client:
        monkeypatch.setattr(client, "_get", fake_get)
        result = client.get_block_transactions(VALID_BLOCK_HASH, 25)

    assert requested_paths == [f"/block/{VALID_BLOCK_HASH}/txs/25"]
    assert len(result) == 1
    assert result[0].txid == txid
    assert result[0].status == {
        "confirmed": True,
        "block_hash": VALID_BLOCK_HASH,
    }


@pytest.mark.parametrize("start_index", [-1, True, 1.5, "25"])
def test_get_block_transactions_rejects_invalid_start_index(start_index):
    with MempoolClient() as client:
        with pytest.raises(ValueError, match="start index"):
            client.get_block_transactions(VALID_BLOCK_HASH, start_index)


def test_get_block_transactions_rejects_invalid_block_hash():
    with MempoolClient() as client:
        with pytest.raises(ValueError, match="block hash"):
            client.get_block_transactions("invalid", 0)


def test_get_block_transactions_rejects_non_list_response(monkeypatch):
    def fake_get(path):
        request = httpx.Request(
            "GET",
            "https://mempool.space/api" + path,
        )
        return httpx.Response(200, json={"transactions": []}, request=request)

    with MempoolClient() as client:
        monkeypatch.setattr(client, "_get", fake_get)

        with pytest.raises(ValueError, match="Unexpected block transactions"):
            client.get_block_transactions(VALID_BLOCK_HASH, 0)


def test_get_block_status_returns_valid_status(monkeypatch):
    requested_paths = []

    def fake_get(path):
        requested_paths.append(path)
        request = httpx.Request(
            "GET",
            "https://mempool.space/api" + path,
        )
        return httpx.Response(
            200,
            json={"in_best_chain": True, "next_best": None},
            request=request,
        )

    with MempoolClient() as client:
        monkeypatch.setattr(client, "_get", fake_get)
        result = client.get_block_status(VALID_BLOCK_HASH)

    assert requested_paths == [
        f"/block/{VALID_BLOCK_HASH}/status"
    ]
    assert result["in_best_chain"] is True


def test_get_block_status_accepts_block_outside_best_chain(monkeypatch):
    def fake_get(path):
        request = httpx.Request(
            "GET",
            "https://mempool.space/api" + path,
        )
        return httpx.Response(
            200,
            json={"in_best_chain": False, "next_best": "b" * 64},
            request=request,
        )

    with MempoolClient() as client:
        monkeypatch.setattr(client, "_get", fake_get)
        result = client.get_block_status(VALID_BLOCK_HASH)

    assert result["in_best_chain"] is False


def test_get_block_status_rejects_invalid_hash():
    with MempoolClient() as client:
        with pytest.raises(ValueError, match="block hash"):
            client.get_block_status("invalid")


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"in_best_chain": "true"},
        {"in_best_chain": 1},
        {"in_best_chain": None},
    ],
)
def test_get_block_status_rejects_invalid_response(monkeypatch, payload):
    def fake_get(path):
        request = httpx.Request(
            "GET",
            "https://mempool.space/api" + path,
        )
        return httpx.Response(200, json=payload, request=request)

    with MempoolClient() as client:
        monkeypatch.setattr(client, "_get", fake_get)

        with pytest.raises(ValueError, match="(?i)block status"):
            client.get_block_status(VALID_BLOCK_HASH)


def test_get_retries_temporary_server_error(monkeypatch):
    responses = iter([
        httpx.Response(
            503,
            request=httpx.Request("GET", "https://mempool.space/api/test"),
        ),
        httpx.Response(
            200,
            text="success",
            request=httpx.Request("GET", "https://mempool.space/api/test"),
        ),
    ])
    calls = []
    delays = []

    def fake_get(path):
        calls.append(path)
        return next(responses)

    monkeypatch.setattr(httpx.Client, "get", lambda self, path: fake_get(path))
    monkeypatch.setattr("src.data.mempool_client.time.sleep", delays.append)

    with MempoolClient() as client:
        response = client._get("/test")

    assert response.status_code == 200
    assert len(calls) == 2
    assert delays == [0.5]


def test_get_respects_numeric_retry_after_header(monkeypatch):
    responses = iter([
        httpx.Response(
            429,
            headers={"Retry-After": "2"},
            request=httpx.Request("GET", "https://mempool.space/api/test"),
        ),
        httpx.Response(
            200,
            text="success",
            request=httpx.Request("GET", "https://mempool.space/api/test"),
        ),
    ])
    delays = []

    monkeypatch.setattr(
        httpx.Client,
        "get",
        lambda self, path: next(responses),
    )
    monkeypatch.setattr("src.data.mempool_client.time.sleep", delays.append)

    with MempoolClient() as client:
        response = client._get("/test")

    assert response.status_code == 200
    assert delays == [2.0]


def test_get_does_not_retry_permanent_client_error(monkeypatch):
    calls = []

    def fake_get(self, path):
        calls.append(path)
        return httpx.Response(
            404,
            request=httpx.Request("GET", "https://mempool.space/api/test"),
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with MempoolClient() as client:
        with pytest.raises(httpx.HTTPStatusError):
            client._get("/test")

    assert calls == ["/test"]


def test_get_stops_after_maximum_retry_attempts(monkeypatch):
    calls = []
    delays = []

    def fake_get(self, path):
        calls.append(path)
        return httpx.Response(
            503,
            request=httpx.Request("GET", "https://mempool.space/api/test"),
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    monkeypatch.setattr("src.data.mempool_client.time.sleep", delays.append)

    with MempoolClient() as client:
        with pytest.raises(httpx.HTTPStatusError):
            client._get("/test")

    assert len(calls) == 3
    assert delays == [0.5, 1.0]


def test_get_retries_connection_error(monkeypatch):
    calls = []
    delays = []

    def fake_get(self, path):
        calls.append(path)
        if len(calls) == 1:
            raise httpx.ConnectError("temporary connection failure")
        return httpx.Response(
            200,
            text="success",
            request=httpx.Request("GET", "https://mempool.space/api/test"),
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    monkeypatch.setattr("src.data.mempool_client.time.sleep", delays.append)

    with MempoolClient() as client:
        response = client._get("/test")

    assert response.status_code == 200
    assert len(calls) == 2
    assert delays == [0.5]
