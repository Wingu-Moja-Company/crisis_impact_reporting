"""
Create a new crisis event document in Cosmos DB and load its form schema.

Usage:
    python scripts/create_crisis_event.py \
        --id ke-flood-2026-04 \
        --name "Kenya Nairobi Floods — April 2026" \
        --country KE --region nairobi --crisis-nature flood \
        --schema-file schemas/flood-schema.json
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from azure.cosmos import CosmosClient


def _container(name: str):
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client(name)


def create(event_id: str, name: str, country: str, region: str, crisis_nature: str, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text())
    schema["crisis_event_id"] = event_id

    doc = {
        "id": event_id,
        "name": name,
        "country_code": country.upper(),
        "region": region.lower(),
        "crisis_nature": crisis_nature,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "form_schema": schema,
    }

    _container("crisis_events").upsert_item(doc)
    print(f"Crisis event '{event_id}' created.")
    print(f"  Name:   {name}")
    print(f"  Region: {region}, {country}")
    print(f"  Nature: {crisis_nature}")
    print(f"  Schema: {len(schema.get('modular_fields', []))} modular field(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a crisis event in Cosmos DB")
    parser.add_argument("--id",            required=True)
    parser.add_argument("--name",          required=True)
    parser.add_argument("--country",       required=True)
    parser.add_argument("--region",        required=True)
    parser.add_argument("--crisis-nature", required=True, dest="crisis_nature")
    parser.add_argument("--schema-file",   required=True, type=Path, dest="schema_file")
    args = parser.parse_args()

    if not args.schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {args.schema_file}")

    create(args.id, args.name, args.country, args.region, args.crisis_nature, args.schema_file)


if __name__ == "__main__":
    main()
