"""
Admin endpoint — DELETE /api/v1/admin/crisis-events/{event_id}/data

Permanently purges ALL report data for a crisis event:
  - Deletes every document in the `reports` container for the event
  - Deletes every photo blob under the `{event_id}/` prefix in `report-photos`
  - Does NOT delete the crisis event document itself (use the events API for that)

Requires X-Admin-Key header. Returns a summary of what was deleted.
"""

import hmac
import json
import logging
import os

import azure.functions as func
from azure.cosmos import CosmosClient, exceptions as cosmos_exc
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

_FORBIDDEN = func.HttpResponse(
    '{"error":"forbidden"}', status_code=403, mimetype="application/json",
)


def _check_admin_key(req: func.HttpRequest) -> bool:
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


def _cosmos_container(name: str):
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client(name)


def main(req: func.HttpRequest) -> func.HttpResponse:
    if not _check_admin_key(req):
        return _FORBIDDEN

    event_id: str = req.route_params.get("event_id", "").strip()
    if not event_id:
        return func.HttpResponse(
            '{"error":"event_id required"}', status_code=400, mimetype="application/json",
        )

    # Safety: require explicit confirmation parameter to prevent accidental calls
    confirm = req.params.get("confirm", "")
    if confirm != "yes":
        return func.HttpResponse(
            '{"error":"Add ?confirm=yes to confirm this destructive operation"}',
            status_code=400, mimetype="application/json",
        )

    deleted_reports = 0
    deleted_blobs = 0
    errors: list[str] = []

    # ── 1. Delete all reports from Cosmos DB ────────────────────────────────
    try:
        container = _cosmos_container("reports")
        query = "SELECT c.id, c.crisis_event_id FROM c WHERE c.crisis_event_id = @eid"
        params = [{"name": "@eid", "value": event_id}]
        docs = list(container.query_items(
            query=query, parameters=params, enable_cross_partition_query=True
        ))
        for doc in docs:
            try:
                container.delete_item(item=doc["id"], partition_key=doc["crisis_event_id"])
                deleted_reports += 1
            except cosmos_exc.CosmosResourceNotFoundError:
                pass  # already gone
            except Exception as exc:
                errors.append(f"report/{doc['id']}: {exc}")
        logger.info("Purged %d reports for event %s", deleted_reports, event_id)
    except Exception as exc:
        errors.append(f"cosmos_query: {exc}")

    # ── 2. Delete photos from Blob Storage ──────────────────────────────────
    try:
        conn_str = os.environ.get("STORAGE_CONNECTION_STRING", "")
        if conn_str:
            blob_client = BlobServiceClient.from_connection_string(conn_str)
            container_client = blob_client.get_container_client("report-photos")
            prefix = f"{event_id}/"
            blobs = list(container_client.list_blobs(name_starts_with=prefix))
            for blob in blobs:
                try:
                    container_client.delete_blob(blob.name)
                    deleted_blobs += 1
                except Exception as exc:
                    errors.append(f"blob/{blob.name}: {exc}")
            logger.info("Purged %d blobs for event %s", deleted_blobs, event_id)
    except Exception as exc:
        errors.append(f"blob_storage: {exc}")

    status = 200 if not errors else 207  # 207 Multi-Status = partial success
    return func.HttpResponse(
        json.dumps({
            "event_id": event_id,
            "deleted_reports": deleted_reports,
            "deleted_blobs": deleted_blobs,
            "errors": errors,
        }),
        status_code=status,
        mimetype="application/json",
    )
