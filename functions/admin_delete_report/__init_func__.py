"""
Admin endpoint — DELETE /api/v1/admin/reports/{report_id}
Permanently removes a report document from Cosmos DB.
Requires X-Admin-Key header.
"""

import hmac
import json
import logging
import os

import azure.functions as func
from azure.cosmos import CosmosClient, exceptions as cosmos_exc

logger = logging.getLogger(__name__)

_FORBIDDEN = func.HttpResponse(
    '{"error":"forbidden"}', status_code=403, mimetype="application/json",
)
_NOT_FOUND = func.HttpResponse(
    '{"error":"not_found"}', status_code=404, mimetype="application/json",
)


def _check_admin_key(req: func.HttpRequest) -> bool:
    admin_key   = os.environ.get("ADMIN_API_KEY", "")
    ingest_key  = os.environ.get("INGEST_API_KEY", "")
    if not admin_key and not ingest_key:
        return True  # open in dev
    provided = req.headers.get("X-Admin-Key", "") or req.headers.get("X-API-Key", "")
    if not provided:
        return False
    if admin_key and hmac.compare_digest(provided, admin_key):
        return True
    if ingest_key and hmac.compare_digest(provided, ingest_key):
        return True
    return False


def main(req: func.HttpRequest) -> func.HttpResponse:
    if not _check_admin_key(req):
        return _FORBIDDEN

    report_id: str = req.route_params.get("report_id", "")
    if not report_id:
        return func.HttpResponse(
            '{"error":"report_id required"}', status_code=400, mimetype="application/json",
        )

    # crisis_event_id is the partition key — caller must supply it as query param
    crisis_event_id = req.params.get("crisis_event_id", "")
    if not crisis_event_id:
        return func.HttpResponse(
            '{"error":"crisis_event_id query param required"}',
            status_code=400, mimetype="application/json",
        )

    endpoint = os.environ["COSMOS_ENDPOINT"]
    key = os.environ["COSMOS_KEY"]
    client = CosmosClient(endpoint, credential=key)
    db_name = os.environ.get("COSMOS_DATABASE", "crisis_db")
    container = client.get_database_client(db_name).get_container_client("reports")

    try:
        container.delete_item(item=report_id, partition_key=crisis_event_id)
        logger.info("Deleted report %s (crisis_event_id=%s)", report_id, crisis_event_id)
        return func.HttpResponse(
            json.dumps({"deleted": report_id}),
            status_code=200,
            mimetype="application/json",
        )
    except cosmos_exc.CosmosResourceNotFoundError:
        return _NOT_FOUND
    except Exception as exc:
        logger.exception("Error deleting report %s", report_id)
        return func.HttpResponse(
            json.dumps({"error": str(exc)}), status_code=500, mimetype="application/json",
        )
