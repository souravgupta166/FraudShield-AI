from collections import Counter
from pathlib import Path
import json
import xml.etree.ElementTree as ET


XML_PATH = Path("data/raw/ofac_sdn_enhanced.xml")
BITCOIN_FEATURE_TYPE = "Digital Currency Address - XBT"
SAMPLE_LIMIT = 10


def local_name(tag: str) -> str:
    """Remove an XML namespace from an element name."""
    return tag.rsplit("}", 1)[-1]


def children(element, name):
    return [
        child for child in element
        if local_name(child.tag) == name
    ]


def first_child(element, name):
    matches = children(element, name)
    return matches[0] if matches else None


def text_of(element, name):
    child = first_child(element, name)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def primary_name(entity):
    names_container = first_child(entity, "names")
    if names_container is None:
        return None

    names = children(names_container, "name")

    # Prefer the entity's primary name.
    names.sort(
        key=lambda item: item.findtext(
            "{*}isPrimary", default="false"
        ).lower() != "true"
    )

    for name in names:
        translations_container = first_child(name, "translations")
        if translations_container is None:
            continue

        translations = children(translations_container, "translation")
        translations.sort(
            key=lambda item: item.findtext(
                "{*}isPrimary", default="false"
            ).lower() != "true"
        )

        for translation in translations:
            full_name = text_of(translation, "formattedFullName")
            if full_name:
                return full_name

    return None


def extract_entity(entity):
    entity_id = entity.attrib.get("id")

    general_info = first_child(entity, "generalInfo")
    entity_type = (
        text_of(general_info, "entityType")
        if general_info is not None else None
    )

    programmes_container = first_child(entity, "sanctionsPrograms")
    programmes = (
        [item.text.strip() for item in children(programmes_container, "sanctionsProgram")
         if item.text and item.text.strip()]
        if programmes_container is not None else []
    )

    features_container = first_child(entity, "features")
    if features_container is None:
        return []

    extracted = []

    for feature in children(features_container, "feature"):
        feature_type = text_of(feature, "type")

        if feature_type != BITCOIN_FEATURE_TYPE:
            continue

        address = text_of(feature, "value")
        if not address:
            continue

        reliability = first_child(feature, "reliability")

        extracted.append({
            "blockchain": "bitcoin",
            "address": address,
            "entity_id": entity_id,
            "entity_name": primary_name(entity),
            "entity_type": entity_type,
            "sanctions_programmes": programmes,
            "source_record_id": feature.attrib.get("id"),
            "version_id": text_of(feature, "versionId"),
            "is_primary": (
                text_of(feature, "isPrimary") or "false"
            ).lower() == "true",
            "reliability": (
                reliability.text.strip()
                if reliability is not None and reliability.text
                else None
            ),
        })

    return extracted


def main():
    if not XML_PATH.is_file():
        raise FileNotFoundError(f"OFAC XML not found: {XML_PATH}")

    address_counts = Counter()
    samples = []
    entity_count = 0
    entities_with_bitcoin = 0
    address_record_count = 0

    print(f"Reading: {XML_PATH}")
    print("Mode: DRY RUN — no database writes")
    print("Parsing XML incrementally...\n")

    for event, element in ET.iterparse(XML_PATH, events=("end",)):
        if local_name(element.tag) != "entity":
            continue

        entity_count += 1
        records = extract_entity(element)

        if records:
            entities_with_bitcoin += 1

        for record in records:
            address_record_count += 1
            address_counts[record["address"]] += 1

            if len(samples) < SAMPLE_LIMIT:
                samples.append(record)

        # Release the processed entity to limit memory use.
        element.clear()

    duplicate_addresses = {
        address: count
        for address, count in address_counts.items()
        if count > 1
    }

    report = {
        "xml_file": str(XML_PATH),
        "mode": "dry_run",
        "entities_scanned": entity_count,
        "entities_with_bitcoin_addresses": entities_with_bitcoin,
        "bitcoin_address_records": address_record_count,
        "unique_bitcoin_addresses": len(address_counts),
        "duplicate_address_values": len(duplicate_addresses),
        "duplicate_record_occurrences": sum(
            count - 1 for count in duplicate_addresses.values()
        ),
        "samples": samples,
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
