import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.inspect_ofac_sdn import (
    XML_PATH,
    BITCOIN_FEATURE_TYPE,
    extract_entity,
    local_name,
)


SOURCE_URL = (
    "https://sanctionslistservice.ofac.treas.gov/"
    "api/PublicationPreview/exports/SDN_ENHANCED.XML"
)
SOURCE_NAME = "OFAC Specially Designated Nationals - Enhanced XML"


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_publication_date(path: Path) -> datetime:
    for _, element in ET.iterparse(path, events=("end",)):
        if local_name(element.tag) != "publicationInfo":
            continue

        for child in element:
            if local_name(child.tag) == "dataAsOf" and child.text:
                return datetime.fromisoformat(child.text.strip())

    raise ValueError("OFAC publicationInfo/dataAsOf was not found.")


def collect_records(path: Path):
    records = []
    entities_scanned = 0
    entities_with_bitcoin = 0

    for _, entity in ET.iterparse(path, events=("end",)):
        if local_name(entity.tag) != "entity":
            continue

        entities_scanned += 1
        entity_records = extract_entity(entity)

        if entity_records:
            entities_with_bitcoin += 1

        for record in entity_records:
            required = (
                "address",
                "entity_id",
                "entity_name",
                "source_record_id",
            )

            missing = [
                field for field in required
                if not record.get(field)
            ]

            if missing:
                raise ValueError(
                    "OFAC record is missing required fields "
                    f"{missing}: {record}"
                )

            records.append(record)

        entity.clear()

    if not records:
        raise ValueError("No Bitcoin sanctions address records were found.")

    feature_ids = [record["source_record_id"] for record in records]

    if len(feature_ids) != len(set(feature_ids)):
        raise ValueError("Duplicate OFAC feature IDs detected; refusing import.")

    return records, entities_scanned, entities_with_bitcoin


def build_report(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"OFAC XML not found: {path}")

    published_at = read_publication_date(path)
    records, entity_count, entities_with_bitcoin = collect_records(path)

    address_counts = Counter(
        record["address"] for record in records
    )

    duplicate_addresses = {
        address: count
        for address, count in address_counts.items()
        if count > 1
    }

    checksum = calculate_sha256(path)

    report = {
        "mode": "dry_run",
        "source_name": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "xml_file": str(path),
        "file_size_bytes": path.stat().st_size,
        "sha256": checksum,
        "data_as_of": published_at.isoformat(),
        "source_key": (
            f"ofac_sdn_enhanced_{published_at.date().isoformat()}"
        ),
        "entities_scanned": entity_count,
        "entities_with_bitcoin_addresses": entities_with_bitcoin,
        "bitcoin_feature_records": len(records),
        "unique_bitcoin_addresses": len(address_counts),
        "duplicate_address_values": len(duplicate_addresses),
        "duplicate_record_occurrences": sum(
            count - 1 for count in duplicate_addresses.values()
        ),
        "distinct_entity_ids": len({
            record["entity_id"] for record in records
        }),
        "distinct_feature_ids": len(set(
            record["source_record_id"] for record in records
        )),
        "samples": records[:5],
        "duplicate_details": {
            address: [
                {
                    "entity_id": record["entity_id"],
                    "entity_name": record["entity_name"],
                    "source_record_id": record["source_record_id"],
                }
                for record in records
                if record["address"] == address
            ]
            for address in duplicate_addresses
        },
    }

    return report, records, published_at


def import_records(report, records, published_at):
    from sqlalchemy import create_engine, delete, select, update
    from sqlalchemy.orm import sessionmaker

    from src.data.database_models import (
        SanctionsSource,
        SanctionedCryptoAddress,
    )

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. No database changes were made."
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    imported_at = datetime.now(timezone.utc)

    try:
        with SessionLocal.begin() as session:
            source = session.scalar(
                select(SanctionsSource).where(
                    SanctionsSource.source_key == report["source_key"]
                )
            )

            if source and source.checksum_sha256 != report["sha256"]:
                raise ValueError(
                    "This source key already exists with a different checksum. "
                    "Refusing to overwrite a different OFAC snapshot."
                )

            if source is None:
                source = SanctionsSource(
                    source_key=report["source_key"],
                    source_name=SOURCE_NAME,
                    source_url=SOURCE_URL,
                    dataset_version=report["data_as_of"],
                    checksum_sha256=report["sha256"],
                    published_at=published_at,
                    imported_at=imported_at,
                    record_count=len(records),
                    is_active=False,
                    metadata_json={},
                )
                session.add(source)
                session.flush()
            else:
                # Re-import the same verified snapshot atomically.
                session.execute(
                    delete(SanctionedCryptoAddress).where(
                        SanctionedCryptoAddress.source_id == source.source_id
                    )
                )

                source.imported_at = imported_at
                source.record_count = len(records)
                source.dataset_version = report["data_as_of"]
                source.published_at = published_at

            source.metadata_json = {
                "data_as_of": report["data_as_of"],
                "file_name": Path(report["xml_file"]).name,
                "file_size_bytes": report["file_size_bytes"],
                "entities_scanned": report["entities_scanned"],
                "entities_with_bitcoin_addresses": (
                    report["entities_with_bitcoin_addresses"]
                ),
                "unique_bitcoin_addresses": (
                    report["unique_bitcoin_addresses"]
                ),
                "duplicate_address_values": (
                    report["duplicate_address_values"]
                ),
                "duplicate_record_occurrences": (
                    report["duplicate_record_occurrences"]
                ),
                "feature_type": BITCOIN_FEATURE_TYPE,
            }

            address_rows = []

            for record in records:
                address_rows.append(
                    SanctionedCryptoAddress(
                        source_id=source.source_id,
                        blockchain="bitcoin",
                        address=record["address"],
                        entity_id=record["entity_id"],
                        entity_name=record["entity_name"],
                        sanctions_program=(
                            record["sanctions_programmes"][0]
                            if record["sanctions_programmes"]
                            else None
                        ),
                        source_record_id=record["source_record_id"],
                        raw_record={
                            **record,
                            "source_name": SOURCE_NAME,
                            "source_url": SOURCE_URL,
                            "data_as_of": report["data_as_of"],
                            "sha256": report["sha256"],
                        },
                    )
                )

            session.add_all(address_rows)

            # Activate this snapshot only after all its records are staged
            # in the same transaction. Previous snapshots remain stored.
            session.execute(
                update(SanctionsSource)
                .where(SanctionsSource.source_id != source.source_id)
                .values(is_active=False)
            )
            source.is_active = True

            session.flush()

            print(
                f"Imported {len(address_rows)} OFAC feature records "
                f"under source {report['source_key']}."
            )

    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Import official OFAC Bitcoin sanctions addresses."
    )
    parser.add_argument(
        "--import",
        dest="do_import",
        action="store_true",
        help="Write the validated snapshot to PostgreSQL.",
    )
    args = parser.parse_args()

    report, records, published_at = build_report(XML_PATH)

    if args.do_import:
        report["mode"] = "import"
        import_records(report, records, published_at)
    else:
        print("DRY RUN ONLY — no database writes.")

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
