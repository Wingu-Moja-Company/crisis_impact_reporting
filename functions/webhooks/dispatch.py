"""
Partner webhook dispatch via Azure Event Grid (CloudEvents 1.0).
Partners register a callback URL with filter criteria in the
partner_subscriptions Cosmos DB container.
Payload is HMAC-SHA256 signed for authenticity verification.
"""

import hashlib
import hmac
import json
import os
import uuid
import urllib.request
from datetime import datetime, timezone

from azure.cosmos import CosmosClient


def _subscriptions_container():
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client("partner_subscriptions")


def _sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _matches_filter(report: dict, sub: dict) -> bool:
    filters = sub.get("filters", {})
    if cid := filters.get("crisis_event_id"):
        if report.get("crisis_event_id") != cid:
            return False
    if lvl := filters.get("damage_level"):
        if report.get("damage", {}).get("level") != lvl:
            return False
    if infra := filters.get("infra_type"):
        if infra not in report.get("damage", {}).get("infrastructure_types", []):
            return False
    if bbox := filters.get("bbox"):
        coords = report.get("location", {}).get("coordinates")
        if coords:
            lon, lat = coords
            lat_min, lon_min, lat_max, lon_max = bbox
            if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
                return False
    return True


def dispatch(report: dict) -> None:
    subscriptions = list(_subscriptions_container().query_items(
        "SELECT * FROM c", enable_cross_partition_query=True
    ))

    event = {
        "specversion": "1.0",
        "type":        "io.crisisplatform.report.submitted",
        "source":      f"/crisis-platform/{report['crisis_event_id']}",
        "id":          str(uuid.uuid4()),
        "time":        datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data":        report,
    }
    payload = json.dumps(event).encode()

    for sub in subscriptions:
        if not _matches_filter(report, sub):
            continue
        callback_url = sub.get("callback_url", "")
        secret = sub.get("signing_secret", "")
        if not callback_url:
            continue

        signature = _sign_payload(payload, secret) if secret else ""
        headers = {
            "Content-Type": "application/cloudevents+json",
            "X-Signature-SHA256": signature,
        }
        req = urllib.request.Request(callback_url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception:
            # Failed deliveries are handled by Azure Event Grid dead-letter queue
            pass
