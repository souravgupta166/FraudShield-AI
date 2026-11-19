# FraudShield AI — Transaction Data Dictionary

## 1. Purpose

This document defines the canonical transaction schema used by
FraudShield AI.

The objective is to standardise transaction records from different
sources before feature engineering, analytics and model development.

## 2. Canonical Transaction Schema

| Field | Data Type | Description |
|---|---|---|
| transaction_id | string | Unique transaction identifier |
| event_step | integer | Relative transaction time or sequence |
| event_time_utc | timestamp, nullable | Actual event timestamp when available |
| transaction_type | string | Transaction category |
| amount | decimal | Transaction amount |
| currency | string | ISO currency code when available |
| sender_account_id | string | Originating account identifier |
| receiver_account_id | string | Destination account identifier |
| sender_balance_before | decimal, nullable | Sender balance before transaction |
| sender_balance_after | decimal, nullable | Sender balance after transaction |
| receiver_balance_before | decimal, nullable | Receiver balance before transaction |
| receiver_balance_after | decimal, nullable | Receiver balance after transaction |
| is_fraud | boolean, nullable | Ground-truth fraud label |
| is_flagged_fraud | boolean, nullable | Existing rule-based fraud flag |
| source_dataset | string | Dataset provenance |

## 3. Data Quality Rules

1. Transaction identifiers must be unique within the source dataset.
2. Transaction amounts must be non-negative.
3. Account identifiers must be preserved as strings.
4. Transaction types must belong to the documented source categories.
5. Missing values must be measured and documented.
6. Fraud labels must contain only valid binary values when available.
7. Original raw data must never be overwritten during processing.
8. Source-specific fields must be retained in the raw layer.

## 4. Fraud Modelling Rules

The following fields are labels or existing detection outputs,
not ordinary predictive features:

- is_fraud
- is_flagged_fraud

These fields must be excluded from model input features unless
a specific evaluation experiment explicitly requires them.

Data splits must respect transaction chronology where applicable.

## 5. PaySim Source Mapping

The initial PaySim dataset is expected to contain these fields:

| PaySim Field | Canonical Field |
|---|---|
| step | event_step |
| type | transaction_type |
| amount | amount |
| nameOrig | sender_account_id |
| nameDest | receiver_account_id |
| oldbalanceOrg | sender_balance_before |
| newbalanceOrig | sender_balance_after |
| oldbalanceDest | receiver_balance_before |
| newbalanceDest | receiver_balance_after |
| isFraud | is_fraud |
| isFlaggedFraud | is_flagged_fraud |

PaySim does not provide a genuine transaction timestamp or
a standard ISO currency code in its usual dataset format.
We will not invent either value.

## 6. Dataset Limitations

PaySim is a synthetic mobile-money transaction dataset.
Its records should not be represented as actual bank customer
transactions.

Dataset provenance, licence and limitations must be documented
before the data is incorporated into the project.
