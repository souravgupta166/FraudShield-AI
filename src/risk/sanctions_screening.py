"""Exact-match Bitcoin address screening against the active OFAC snapshot."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.database_models import (
    SanctionedCryptoAddress,
    SanctionsSource,
)


INVESTIGATION_NOTE = (
    "An exact address match indicates that the address appears in the cited "
    "sanctions dataset. It is a screening result, not proof of ownership, "
    "criminal activity, or a conclusion that a transaction is illicit. "
    "Verify the source record and current official sanctions information."
)


def screen_bitcoin_address(
    session: Session,
    address: str,
) -> dict:
    """
    Screen a Bitcoin address against all records in the active OFAC snapshot.

    Matching is exact and case-sensitive. All matching feature records are
    returned, including multiple records associated with the same address.
    """

    if not isinstance(address, str) or not address.strip():
        raise ValueError("Bitcoin address must be a non-empty string.")

    normalized_address = address.strip()

    statement = (
        select(SanctionedCryptoAddress, SanctionsSource)
        .join(
            SanctionsSource,
            SanctionedCryptoAddress.source_id == SanctionsSource.source_id,
        )
        .where(
            SanctionsSource.is_active.is_(True),
            SanctionedCryptoAddress.blockchain == "bitcoin",
            SanctionedCryptoAddress.address == normalized_address,
        )
        .order_by(
            SanctionedCryptoAddress.entity_id,
            SanctionedCryptoAddress.source_record_id,
        )
    )

    rows = session.execute(statement).all()

    matches = []

    for address_record, source in rows:
        raw_record = address_record.raw_record or {}
        source_metadata = source.metadata_json or {}

        matches.append(
            {
                "blockchain": address_record.blockchain,
                "address": address_record.address,
                "entity_id": address_record.entity_id,
                "entity_name": address_record.entity_name,
                "source_record_id": address_record.source_record_id,
                "sanctions_program": address_record.sanctions_program,
                "sanctions_programmes": raw_record.get(
                    "sanctions_programmes",
                    [],
                ),
                "entity_type": raw_record.get("entity_type"),
                "feature_version_id": raw_record.get("version_id"),
                "is_primary": raw_record.get("is_primary"),
                "reliability": raw_record.get("reliability"),
                "source": {
                    "name": source.source_name,
                    "url": source.source_url,
                    "source_key": source.source_key,
                    "dataset_version": source.dataset_version,
                    "published_at": (
                        source.published_at.isoformat()
                        if source.published_at
                        else None
                    ),
                    "data_as_of": source_metadata.get("data_as_of"),
                    "checksum_sha256": source.checksum_sha256,
                },
            }
        )

    return {
        "blockchain": "bitcoin",
        "address": normalized_address,
        "match_status": "exact_match" if matches else "no_match",
        "is_sanctioned_address_match": bool(matches),
        "match_count": len(matches),
        "matches": matches,
        "investigation_note": INVESTIGATION_NOTE,
    }
