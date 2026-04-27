#!/usr/bin/env python3
"""
Seed a default v1 schema for a crisis event.

Usage:
    python scripts/seed_default_schema.py --crisis-id ke-flood-dev [--crisis-nature flood]

Requires env vars (or functions/local.settings.json):
    COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE

The 'schemas' Cosmos container is created if it does not exist.
Idempotent — safe to re-run; will not overwrite an existing schema unless --force is passed.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Allow importing from the functions package
_FUNCTIONS_DIR = Path(__file__).parent.parent / "functions"
sys.path.insert(0, str(_FUNCTIONS_DIR))


def _load_env_from_local_settings():
    """Load COSMOS_* env vars from functions/local.settings.json if present."""
    settings_path = _FUNCTIONS_DIR / "local.settings.json"
    if not settings_path.exists():
        return
    try:
        data = json.loads(settings_path.read_text())
        for k, v in data.get("Values", {}).items():
            if k not in os.environ:
                os.environ[k] = str(v)
    except Exception as exc:
        print(f"Warning: could not load local.settings.json: {exc}", file=sys.stderr)


def _ensure_schemas_container():
    """Create the 'schemas' Cosmos container if it doesn't exist."""
    from azure.cosmos import CosmosClient, PartitionKey

    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    db = client.get_database_client(os.environ["COSMOS_DATABASE"])
    try:
        db.create_container_if_not_exists(
            id="schemas",
            partition_key=PartitionKey(path="/crisis_event_id"),
            offer_throughput=400,
        )
        print("Ensured 'schemas' container exists.")
    except Exception as exc:
        print(f"Warning: could not verify schemas container: {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Seed default v1 schema for a crisis event")
    parser.add_argument("--crisis-id", required=True, help="Crisis event ID, e.g. ke-flood-dev")
    parser.add_argument(
        "--crisis-nature",
        default="flood",
        choices=["flood", "earthquake", "hurricane", "wildfire", "conflict", "generic"],
        help="Crisis nature — determines which default field set to use (default: flood)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force publish even if a schema already exists (creates a new version)",
    )
    args = parser.parse_args()

    _load_env_from_local_settings()

    for var in ("COSMOS_ENDPOINT", "COSMOS_KEY", "COSMOS_DATABASE"):
        if not os.environ.get(var):
            print(f"ERROR: {var} is not set", file=sys.stderr)
            sys.exit(1)

    _ensure_schemas_container()

    from schema.defaults import get_default_schema
    from schema.service import get_version_only, publish_schema, seed_schema

    schema_body = get_default_schema(args.crisis_nature)

    if args.force:
        doc = publish_schema(args.crisis_id, schema_body, published_by="seed-script")
        print(f"Published schema v{doc['version']} for {args.crisis_id}")
    else:
        current = get_version_only(args.crisis_id)
        if current is not None:
            print(
                f"Schema already exists for {args.crisis_id} (v{current}). "
                "Use --force to publish a new version."
            )
            sys.exit(0)
        doc = seed_schema(args.crisis_id, schema_body)
        if doc:
            print(f"Seeded schema v{doc['version']} for {args.crisis_id}")
        else:
            print("Schema already existed — nothing seeded.")

    print("Done.")


if __name__ == "__main__":
    main()
