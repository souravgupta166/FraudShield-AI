# FraudShield AI — Bitcoin Data Model

## 1. Purpose

This document defines the canonical data model for FraudShield AI.

The platform ingests public Bitcoin blockchain data and converts it into
structured records for transaction monitoring, graph analysis, risk
assessment and investigation.

The model follows Bitcoin's UTXO architecture.

## 2. Core entities

### 2.1 Blocks

| Field | Type | Description |
|---|---|---|
| block_hash | CHAR(64) | Unique block identifier |
| height | BIGINT | Block height |
| timestamp | TIMESTAMPTZ | Block timestamp |
| previous_block_hash | CHAR(64), nullable | Previous block hash |
| chain_status | VARCHAR | Best-chain, orphaned or unknown |
| observed_at | TIMESTAMPTZ | Time observed by our platform |

### 2.2 Transactions

| Field | Type | Description |
|---|---|---|
| txid | CHAR(64) | Transaction identifier |
| wtxid | CHAR(64), nullable | Witness transaction identifier |
| version | INTEGER | Transaction version |
| locktime | BIGINT | Transaction locktime |
| size_bytes | INTEGER | Serialized size |
| weight | INTEGER | Transaction weight |
| fee_sats | BIGINT, nullable | Transaction fee in satoshis |
| status | VARCHAR | Mempool, confirmed or unknown |
| block_hash | CHAR(64), nullable | Containing block |
| first_seen_at | TIMESTAMPTZ | First observation time |
| raw_payload | JSONB | Original API response |

### 2.3 Transaction inputs

Each transaction may contain multiple inputs.

| Field | Type | Description |
|---|---|---|
| txid | CHAR(64) | Spending transaction |
| input_index | INTEGER | Input position |
| previous_txid | CHAR(64), nullable | Referenced previous transaction |
| previous_output_index | INTEGER, nullable | Referenced previous output |
| sequence | BIGINT | Input sequence |
| is_coinbase | BOOLEAN | Whether this is a coinbase input |
| script_sig_hex | TEXT | Input script |
| witness_data | JSONB | Witness stack |

Primary key: txid + input_index.

Coinbase inputs do not reference a previous transaction output.

### 2.4 Transaction outputs

Each transaction may contain multiple outputs.

| Field | Type | Description |
|---|---|---|
| txid | CHAR(64) | Creating transaction |
| output_index | INTEGER | Output position |
| value_sats | BIGINT | Output value in satoshis |
| script_pubkey_hex | TEXT | Locking script |
| script_type | VARCHAR, nullable | Script classification |
| address | TEXT, nullable | Extracted address, if available |

Primary key: txid + output_index.

An output is uniquely identified by its outpoint:
transaction ID + output index.

### 2.5 Addresses

| Field | Type | Description |
|---|---|---|
| address | TEXT | Bitcoin address identifier |
| address_type | VARCHAR, nullable | Address or script classification |
| first_seen_at | TIMESTAMPTZ | First platform observation |
| last_seen_at | TIMESTAMPTZ | Most recent observation |

An address is not necessarily equivalent to a wallet or an individual.

Some scripts do not expose a conventional address. Address extraction
must therefore be optional.

### 2.6 Risk assessments

| Field | Type | Description |
|---|---|---|
| assessment_id | UUID | Unique assessment identifier |
| subject_type | VARCHAR | Transaction or address |
| subject_id | TEXT | Assessed identifier |
| risk_score | NUMERIC(5,2) | Score between 0 and 100 |
| risk_level | VARCHAR | Low, medium, high or critical |
| engine_version | VARCHAR | Risk engine version |
| assessed_at | TIMESTAMPTZ | Assessment timestamp |
| explanation | JSONB | Structured explanation |

Risk assessments are separate from blockchain observations.
An assessment must be reproducible and traceable to its evidence.

## 3. Supporting entities

### Risk evidence

Individual observations supporting a risk assessment:

- Evidence category
- Source
- Reference identifier
- Evidence description
- Confidence or match quality
- Observation timestamp

### Source observations

Track ingestion events:

- Source name
- External record identifier
- Event type
- Payload hash
- Observation timestamp
- Processing status
- Error details, where applicable

## 4. Data integrity rules

1. Store monetary values as integer satoshis.
2. Never use floating-point values for BTC accounting.
3. Preserve original source payloads for auditability.
4. Keep transaction inputs and outputs in separate tables.
5. Use composite keys for input and output positions.
6. Allow nullable previous outpoints for coinbase inputs.
7. Allow nullable addresses for scripts without an extracted address.
8. Do not infer real-world identity from an address.
9. Keep mempool and confirmed transaction states distinguishable.
10. Support block reorganisations and transaction status updates.
11. Record source and observation timestamps.
12. Do not overwrite historical risk assessments.

## 5. Blockchain and reorganisation handling

Transactions can initially be observed in the mempool and later included
in a confirmed block.

A block can also become orphaned during a chain reorganisation.

The platform must therefore distinguish:

- First observed in mempool
- Included in a block
- Confirmed with additional blocks
- No longer in the best chain
- Confirmation status unknown

Historical observations should be retained for audit purposes.

## 6. Risk interpretation

Risk scores represent analytical indicators, not proof of criminal
activity.

The system must distinguish:

- Direct sanctions-list matches
- Potential sanctions matches
- Publicly reported scam indicators
- Behavioural anomalies
- Graph-based risk indicators
- Unverified associations

Evidence quality and source provenance must accompany every assessment.

## 7. Initial data source

Primary source: Mempool.space

REST API documentation:
https://mempool.space/docs/api/rest

WebSocket documentation:
https://mempool.space/docs/api/websocket

The initial implementation will use the public API with conservative
request rates and retry handling.

## 8. Future extensibility

The data model should allow additional chains to be added through
chain-specific ingestion adapters.

Bitcoin-specific UTXO structures must not be incorrectly imposed
on account-based blockchains such as Ethereum.
