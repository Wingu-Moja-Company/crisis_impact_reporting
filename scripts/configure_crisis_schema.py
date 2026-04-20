"""
Update the modular field schema for an existing crisis event in Cosmos DB.
Use this to add or modify form fields after a crisis event has been created,
without redeploying code.

Usage:
    python scripts/configure_crisis_schema.py \
        --crisis-id ke-flood-2026-04 \
        --schema-file schemas/flood-schema.json

    python scripts/configure_crisis_schema.py \
        --crisis-id ke-flood-2026-04 \
        --add-field '{"id":"road_passable","type":"boolean","required":false,"label":{"en":"Is the nearest road passable?","ar":"...","fr":"...","zh":"...","ru":"...","es":"..."}}'
"""

import argparse
import json
import os
import sys
from pathlib import Path

from azure.cosmos import CosmosClient, exceptions


def _container():
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client("crisis_events")


def update_from_file(crisis_id: str, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text())
    schema["crisis_event_id"] = crisis_id

    try:
        doc = _container().read_item(crisis_id, partition_key=crisis_id)
    except exceptions.CosmosResourceNotFoundError:
        print(f"ERROR: crisis event '{crisis_id}' not found. Run create_crisis_event.py first.", file=sys.stderr)
        sys.exit(1)

    doc["form_schema"] = schema
    _container().upsert_item(doc)

    field_count = len(schema.get("modular_fields", []))
    print(f"Schema updated for '{crisis_id}' — {field_count} modular field(s).")


def add_field(crisis_id: str, field_json: str) -> None:
    field = json.loads(field_json)
    required_keys = {"id", "type", "label"}
    if not required_keys.issubset(field.keys()):
        print(f"ERROR: field must have keys: {required_keys}", file=sys.stderr)
        sys.exit(1)

    try:
        doc = _container().read_item(crisis_id, partition_key=crisis_id)
    except exceptions.CosmosResourceNotFoundError:
        print(f"ERROR: crisis event '{crisis_id}' not found.", file=sys.stderr)
        sys.exit(1)

    schema = doc.setdefault("form_schema", {})
    modular = schema.setdefault("modular_fields", [])

    # Replace if field id already exists, otherwise append
    existing_ids = [f["id"] for f in modular]
    if field["id"] in existing_ids:
        modular[existing_ids.index(field["id"])] = field
        action = "updated"
    else:
        modular.append(field)
        action = "added"

    _container().upsert_item(doc)
    print(f"Field '{field['id']}' {action} in crisis event '{crisis_id}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update crisis event form schema in Cosmos DB")
    parser.add_argument("--crisis-id", required=True, dest="crisis_id")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--schema-file", type=Path, dest="schema_file",
                       help="Replace full schema from JSON file")
    group.add_argument("--add-field", dest="add_field",
                       help="Add or replace a single modular field (JSON string)")

    args = parser.parse_args()

    if args.schema_file:
        if not args.schema_file.exists():
            print(f"File not found: {args.schema_file}", file=sys.stderr)
            sys.exit(1)
        update_from_file(args.crisis_id, args.schema_file)
    else:
        add_field(args.crisis_id, args.add_field)


if __name__ == "__main__":
    main()
