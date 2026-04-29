"""
Admin endpoint — PATCH /api/v1/admin/reports/{report_id}
Edits a report document in Cosmos DB.

Accepted JSON body fields (all optional):
  damage_level         : "minimal" | "partial" | "complete"
  infrastructure_types : list[str]
  responses            : dict  — merged into existing responses/modular_fields

Requires X-Admin-Key or X-API-Key header.
"""

import hmac
import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func
from azure.cosmos import CosmosClient, exceptions as cosmos_exc

logger = logging.getLogger(__name__)

_FORBIDDEN = func.HttpResponse(
    '{"error":"forbidden"}', status_code=403, mimetype="application/json",
)
_NOT_FOUND = func.HttpResponse(
    '{"error":"not_found"}', status_code=404, mimetype="application/json",
)
_DAMAGE_VALUES = {"minimal", "partial", "complete"}


def _check_auth(req: func.HttpRequest) -> bool:
    admin_key  = os.environ.get("ADMIN_API_KEY", "")
    ingest_key = os.environ.get("INGEST_API_KEY", "")
    if not admin_key and not ingest_key:
        return True
    provided = req.headers.get("X-Admin-Key", "") or req.headers.get("X-API-Key", "")
    if not provided:
        return False
    if admin_key and hmac.compare_digest(provided, admin_key):
        return True
    if ingest_key and hmac.compare_digest(provided, ingest_key):
        return True
    return False


def main(req: func.HttpRequest) -> func.HttpResponse:
    if not _check_auth(req):
        return _FORBIDDEN

    report_id: str = req.route_params.get("report_id", "")
    crisis_event_id = req.params.get("crisis_event_id", "")
    if not report_id or not crisis_event_id:
        return func.HttpResponse(
            '{"error":"report_id and crisis_event_id required"}',
            status_code=400, mimetype="application/json",
        )

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            '{"error":"invalid JSON body"}', status_code=400, mimetype="application/json",
        )

    endpoint = os.environ["COSMOS_ENDPOINT"]
    key      = os.environ["COSMOS_KEY"]
    db_name  = os.environ.get("COSMOS_DATABASE", "crisis_db")
    client   = CosmosClient(endpoint, credential=key)
    container = client.get_database_client(db_name).get_container_client("reports")

    try:
        doc = container.read_item(item=report_id, partition_key=crisis_event_id)
    except cosmos_exc.CosmosResourceNotFoundError:
        return _NOT_FOUND

    # ── Apply edits ──────────────────────────────────────────────────────────
    changed = False

    if "damage_level" in body:
        lvl = str(body["damage_level"]).lower()
        if lvl not in _DAMAGE_VALUES:
            return func.HttpResponse(
                json.dumps({"error": f"damage_level must be one of {sorted(_DAMAGE_VALUES)}"}),
                status_code=400, mimetype="application/json",
            )
        if "damage" not in doc or not isinstance(doc.get("damage"), dict):
            doc["damage"] = {}
        doc["damage"]["level"] = lvl
        changed = True

    if "infrastructure_types" in body:
        infra = body["infrastructure_types"]
        if not isinstance(infra, list):
            return func.HttpResponse(
                '{"error":"infrastructure_types must be a list"}',
                status_code=400, mimetype="application/json",
            )
        if "damage" not in doc or not isinstance(doc.get("damage"), dict):
            doc["damage"] = {}
        doc["damage"]["infrastructure_types"] = [str(v) for v in infra]
        changed = True

    if "responses" in body and isinstance(body["responses"], dict):
        existing = doc.get("responses") or doc.get("modular_fields") or {}
        existing.update(body["responses"])
        doc["responses"] = existing
        # Remove old modular_fields key to avoid confusion
        doc.pop("modular_fields", None)
        changed = True

    if not changed:
        return func.HttpResponse(
            '{"error":"no editable fields provided"}',
            status_code=400, mimetype="application/json",
        )

    doc["admin_edited_at"] = datetime.now(timezone.utc).isoformat()

    try:
        container.replace_item(item=report_id, body=doc)
        logger.info("Admin edited report %s", report_id)
        return func.HttpResponse(
            json.dumps({"updated": report_id}),
            status_code=200, mimetype="application/json",
        )
    except Exception as exc:
        logger.exception("Error updating report %s", report_id)
        return func.HttpResponse(
            json.dumps({"error": str(exc)}), status_code=500, mimetype="application/json",
        )
