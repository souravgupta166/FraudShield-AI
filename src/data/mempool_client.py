import re
import time
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator


BASE_URL = "https://mempool.space/api"

MAX_REQUEST_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_DELAY_SECONDS = 30.0


class BitcoinTransaction(BaseModel):
    model_config = ConfigDict(extra="allow")

    txid: str
    version: int
    locktime: int
    size: int
    weight: int
    fee: int = Field(ge=0)
    vin: list[dict[str, Any]]
    vout: list[dict[str, Any]]
    status: dict[str, Any]

    @field_validator("txid")
    @classmethod
    def validate_txid(cls, value: str) -> str:
        if not re.fullmatch(r"[a-fA-F0-9]{64}", value):
            raise ValueError("Invalid Bitcoin transaction ID")
        return value.lower()


class MempoolClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "User-Agent": "FraudShieldAI/0.1 (public blockchain research)"
            },
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _get(self, path: str) -> httpx.Response:
        """GET with bounded retries for temporary API/network failures."""
        for attempt in range(MAX_REQUEST_ATTEMPTS):
            try:
                response = self.client.get(path)

                if response.status_code not in RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                    return response

                if attempt == MAX_REQUEST_ATTEMPTS - 1:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")

                try:
                    delay = float(retry_after) if retry_after else (
                        0.5 * (2 ** attempt)
                    )
                except ValueError:
                    delay = 0.5 * (2 ** attempt)

                time.sleep(
                    min(max(delay, 0.0), MAX_RETRY_DELAY_SECONDS)
                )

            except httpx.TransportError:
                if attempt == MAX_REQUEST_ATTEMPTS - 1:
                    raise

                time.sleep(
                    min(
                        0.5 * (2 ** attempt),
                        MAX_RETRY_DELAY_SECONDS,
                    )
                )

        raise RuntimeError("HTTP request retry loop exited unexpectedly")

    def get_tip_height(self) -> int:
        response = self._get("/blocks/tip/height")
        return int(response.text.strip())

    def get_tip_hash(self) -> str:
        block_hash = self._get("/blocks/tip/hash").text.strip()

        if not re.fullmatch(r"[a-fA-F0-9]{64}", block_hash):
            raise ValueError("Mempool API returned an invalid block hash")

        return block_hash.lower()

    def get_block_hash_at_height(self, height: int) -> str:
        if isinstance(height, bool) or not isinstance(height, int) or height < 0:
            raise ValueError("Invalid block height")

        block_hash = self._get(f"/block-height/{height}").text.strip()

        if not re.fullmatch(r"[a-fA-F0-9]{64}", block_hash):
            raise ValueError("Mempool API returned an invalid block hash")

        return block_hash.lower()

    def get_block(self, block_hash: str) -> dict[str, Any]:
        if not re.fullmatch(r"[a-fA-F0-9]{64}", block_hash):
            raise ValueError("Invalid Bitcoin block hash")

        return self._get(f"/block/{block_hash}").json()

    def get_recent_mempool_txids(self) -> list[str]:
        txids = self._get("/mempool/recent").json()

        if not isinstance(txids, list):
            raise ValueError("Unexpected mempool response")

        return [
            txid.lower()
            for txid in txids
            if isinstance(txid, str)
            and re.fullmatch(r"[a-fA-F0-9]{64}", txid)
        ]


    def get_block_txids(self, block_hash: str) -> list[str]:
        if not re.fullmatch(r"[a-fA-F0-9]{64}", block_hash):
            raise ValueError("Invalid Bitcoin block hash")

        txids = self._get(f"/block/{block_hash}/txids").json()

        if not isinstance(txids, list):
            raise ValueError("Unexpected block transaction ID response")

        if not all(
            isinstance(txid, str)
            and re.fullmatch(r"[a-fA-F0-9]{64}", txid)
            for txid in txids
        ):
            raise ValueError("Block response contains an invalid transaction ID")

        return [txid.lower() for txid in txids]

    def get_block_status(self, block_hash: str) -> dict[str, Any]:
        """Return validated chain status for a Bitcoin block."""
        if not re.fullmatch(r"[a-fA-F0-9]{64}", block_hash):
            raise ValueError("Invalid Bitcoin block hash")

        normalized_hash = block_hash.lower()
        payload = self._get(
            f"/block/{normalized_hash}/status"
        ).json()

        if not isinstance(payload, dict):
            raise ValueError("Unexpected block status response")

        if not isinstance(payload.get("in_best_chain"), bool):
            raise ValueError("Block status is missing a valid in_best_chain flag")

        return payload

    def get_block_transactions(
        self,
        block_hash: str,
        start_index: int = 0,
    ) -> list[BitcoinTransaction]:
        """Fetch one page of confirmed transactions from a Bitcoin block.

        The block-transactions endpoint omits transaction status because
        the containing block provides the confirmation context.
        """
        if not re.fullmatch(r"[a-fA-F0-9]{64}", block_hash):
            raise ValueError("Invalid Bitcoin block hash")

        if (
            isinstance(start_index, bool)
            or not isinstance(start_index, int)
            or start_index < 0
        ):
            raise ValueError("Invalid block transaction start index")

        normalized_hash = block_hash.lower()
        payloads = self._get(
            f"/block/{normalized_hash}/txs/{start_index}"
        ).json()

        if not isinstance(payloads, list):
            raise ValueError("Unexpected block transactions response")

        transactions = []

        for payload in payloads:
            if not isinstance(payload, dict):
                raise ValueError("Block transaction must be an object")

            # This endpoint omits status. The requested, validated block
            # supplies the confirmation context for these transactions.
            transaction_payload = {
                **payload,
                "status": {
                    "confirmed": True,
                    "block_hash": normalized_hash,
                },
            }

            transactions.append(
                BitcoinTransaction.model_validate(transaction_payload)
            )

        return transactions

    def get_transaction(self, txid: str) -> BitcoinTransaction:
        if not re.fullmatch(r"[a-fA-F0-9]{64}", txid):
            raise ValueError("Invalid Bitcoin transaction ID")

        payload = self._get(f"/tx/{txid}").json()
        return BitcoinTransaction.model_validate(payload)
