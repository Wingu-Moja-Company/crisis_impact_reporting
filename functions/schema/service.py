"""
Schema service — Cosmos DB read/write operations for dynamic form schemas.

Schema documents live in the 'schemas' container, partitioned by crisis_event_id.
Each version is an immutable snapshot; the current version pointer lives on the
crisis_event document (crisis_events.current_schema_version).

Document id pattern: schema_{crisis_event_id}_v{version}
"""

import logging
import os
from datetime import datetime, timezone

from azure.cosmos import CosmosClient, exceptions as cosmos_exc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _db():
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"])


def _schemas():
    return _db().get_container_client("schemas")


def _events():
    return _db().get_container_client("crisis_events")


def _schema_id(crisis_event_id: str, version: int) -> str:
    return f"schema_{crisis_event_id}_v{version}"


def _get_max_version(crisis_event_id: str) -> int | None:
    """Query the schemas container for the highest stored version number."""
    query = "SELECT VALUE MAX(c.version) FROM c WHERE c.crisis_event_id = @id"
    results = list(
        _schemas().query_items(
            query=query,
            parameters=[{"name": "@id", "value": crisis_event_id}],
            partition_key=crisis_event_id,
        )
    )
    if results and results[0] is not None:
        return int(results[0])
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_schema(crisis_event_id: str) -> dict | None:
    """
    Return the current (latest) schema for a crisis event.
    Reads version pointer from crisis_events doc; falls back to MAX query.
    Returns None if the event or schema does not exist.
    """
    try:
        event = _events().read_item(crisis_event_id, partition_key=crisis_event_id)
    except cosmos_exc.CosmosResourceNotFoundError:
        return None

    version = event.get("current_schema_version")
    if version is None:
        version = _get_max_version(crisis_event_id)
    if version is None:
        return None

    return get_schema_version(crisis_event_id, version)


def get_version_only(crisis_event_id: str) -> int | None:
    """
    Return only the current schema version number (cheap poll endpoint).
    Returns None if the event does not exist.
    """
    try:
        event = _events().read_item(crisis_event_id, partition_key=crisis_event_id)
    except cosmos_exc.CosmosResourceNotFoundError:
        return None

    version = event.get("current_schema_version")
    if version is None:
        version = _get_max_version(crisis_event_id)
    return version


def get_schema_version(crisis_event_id: str, version: int) -> dict | None:
    """
    Return a specific immutable schema version.
    Returns None if that version does not exist.
    """
    doc_id = _schema_id(crisis_event_id, version)
    try:
        return _schemas().read_item(doc_id, partition_key=crisis_event_id)
    except cosmos_exc.CosmosResourceNotFoundError:
        return None


def publish_schema(
    crisis_event_id: str,
    schema_body: dict,
    published_by: str,
) -> dict:
    """
    Publish a new schema version.

    schema_body must contain:
        system_fields: dict
        custom_fields: list[dict]

    Returns the stored schema document (with id, version, published_at, etc).
    Raises on Cosmos errors.
    """
    # Determine next version
    current = _get_max_version(crisis_event_id)
    new_version = (current or 0) + 1

    doc = {
        "id": _schema_id(crisis_event_id, new_version),
        "crisis_event_id": crisis_event_id,
        "version": new_version,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_by": published_by,
        "system_fields": schema_body.get("system_fields", {}),
        "custom_fields": schema_body.get("custom_fields", []),
    }

    _schemas().upsert_item(doc)
    logger.info(
        "Published schema v%d for %s by %s", new_version, crisis_event_id, published_by
    )

    # Update current_schema_version pointer on the crisis_event document
    try:
        event = _events().read_item(crisis_event_id, partition_key=crisis_event_id)
        event["current_schema_version"] = new_version
        _events().upsert_item(event)
    except cosmos_exc.CosmosResourceNotFoundError:
        logger.warning(
            "Crisis event %s not found when updating schema version pointer", crisis_event_id
        )

    return doc


def list_schema_history(crisis_event_id: str) -> list[dict]:
    """
    Return lightweight metadata for all schema versions (no field lists).
    Sorted by version ascending.  Includes custom_field_count for dashboard display.
    """
    query = (
        "SELECT c.id, c.crisis_event_id, c.version, c.published_at, c.published_by, c.custom_fields "
        "FROM c WHERE c.crisis_event_id = @id ORDER BY c.version ASC"
    )
    items = list(_schemas().query_items(
        query=query,
        parameters=[{"name": "@id", "value": crisis_event_id}],
        partition_key=crisis_event_id,
    ))
    for item in items:
        # Add count for dashboard, then remove the full list
        item["custom_field_count"] = len(item.pop("custom_fields", []) or [])
    return items


def seed_schema(crisis_event_id: str, schema_body: dict) -> dict | None:
    """
    Seed v1 schema only if no schema exists yet for this event.
    Safe to call multiple times (idempotent).
    Returns the schema doc if seeded, None if already existed.
    """
    existing = _get_max_version(crisis_event_id)
    if existing is not None:
        logger.info("Schema already exists for %s (v%d) — skip seed", crisis_event_id, existing)
        return None
    return publish_schema(crisis_event_id, schema_body, published_by="system")
