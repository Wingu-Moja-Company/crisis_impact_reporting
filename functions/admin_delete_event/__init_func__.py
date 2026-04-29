"""
Admin endpoint — DELETE /api/v1/admin/crisis-events/{event_id}

Permanently deletes a crisis event and ALL associated data:
  - Every report document in the `reports` container
  - Every photo blob under the `{event_id}/` prefix in `report-photos`
  - Every schema document in the `schemas` container
  - Every building document in the `buildings` container
  - Every building version in the `building_versions` container
  - The crisis event document itself in `crisis_events`

Requires X-Admin-Key header and ?confirm=yes query parameter.
Returns a summary of everything deleted.
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


def _delete_all(container_name: str, event_id: str, id_field: str = "id",
                pk_field: str = "crisis_event_id") -> tuple[int, list[str]]:
    """Delete all documents in a container that belong to event_id. Returns (count, errors)."""
    deleted = 0
    errors: list[str] = []
    try:
        container = _cosmos_container(container_name)
        query = f"SELECT c.{id_field}, c.{pk_field} FROM c WHERE c.{pk_field} = @eid"
        params = [{"name": "@eid", "value": event_id}]
        docs = list(container.query_items(
            query=query, parameters=params, enable_cross_partition_query=True,
        ))
        for doc in docs:
            try:
                container.delete_item(item=doc[id_field], partition_key=doc[pk_field])
                deleted += 1
            except cosmos_exc.CosmosResourceNotFoundError:
                pass
            except Exception as exc:
                errors.append(f"{container_name}/{doc[id_field]}: {exc}")
    except Exception as exc:
        errors.append(f"{container_name} query: {exc}")
    return deleted, errors


def main(req: func.HttpRequest) -> func.HttpResponse:
    if not _check_admin_key(req):
        return _FORBIDDEN

    event_id: str = req.route_params.get("event_id", "").strip()
    if not event_id:
        return func.HttpResponse(
            '{"error":"event_id required"}', status_code=400, mimetype="application/json",
        )

    if req.params.get("confirm", "") != "yes":
        return func.HttpResponse(
            '{"error":"Add ?confirm=yes to confirm this irreversible operation"}',
            status_code=400, mimetype="application/json",
        )

    summary: dict[str, int] = {}
    all_errors: list[str] = []

    # ── 1. Reports ────────────────────────────────────────────────────────────
    n, errs = _delete_all("reports", event_id)
    summary["deleted_reports"] = n
    all_errors.extend(errs)

    # ── 2. Photos (Blob Storage) ───────────────────────────────────────────────
    deleted_blobs = 0
    try:
        conn_str = os.environ.get("STORAGE_CONNECTION_STRING", "")
        if conn_str:
            blob_svc = BlobServiceClient.from_connection_string(conn_str)
            cc = blob_svc.get_container_client("report-photos")
            for blob in list(cc.list_blobs(name_starts_with=f"{event_id}/")):
                try:
                    cc.delete_blob(blob.name)
                    deleted_blobs += 1
                except Exception as exc:
                    all_errors.append(f"blob/{blob.name}: {exc}")
    except Exception as exc:
        all_errors.append(f"blob_storage: {exc}")
    summary["deleted_blobs"] = deleted_blobs

    # ── 3. Schemas ────────────────────────────────────────────────────────────
    n, errs = _delete_all("schemas", event_id)
    summary["deleted_schemas"] = n
    all_errors.extend(errs)

    # ── 4. Buildings ──────────────────────────────────────────────────────────
    n, errs = _delete_all("buildings", event_id,
                          id_field="building_id", pk_field="crisis_event_id")
    summary["deleted_buildings"] = n
    all_errors.extend(errs)

    # ── 5. Building versions ──────────────────────────────────────────────────
    n, errs = _delete_all("building_versions", event_id)
    summary["deleted_building_versions"] = n
    all_errors.extend(errs)

    # ── 6. Crisis event document itself ───────────────────────────────────────
    try:
        _cosmos_container("crisis_events").delete_item(item=event_id, partition_key=event_id)
        summary["deleted_event"] = 1
        logger.info("Deleted crisis event %s and all associated data", event_id)
    except cosmos_exc.CosmosResourceNotFoundError:
        summary["deleted_event"] = 0
    except Exception as exc:
        all_errors.append(f"crisis_events/{event_id}: {exc}")
        summary["deleted_event"] = 0

    status = 200 if not all_errors else 207
    return func.HttpResponse(
        json.dumps({"event_id": event_id, **summary, "errors": all_errors}),
        status_code=status,
        mimetype="application/json",
    )
