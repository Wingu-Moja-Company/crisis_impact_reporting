"""
CAP alert feed — Common Alerting Protocol v1.2 (ISO 22324).
Triggered on 'complete' damage level reports only.
Consumed by national meteorological and civil protection agencies.
"""

import os
import uuid
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring, indent

from azure.cosmos import CosmosClient


def _container(name: str):
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client(name)


def build_cap_feed(crisis_event_id: str, since_minutes: int = 5) -> str:
    """Return a CAP 1.2 XML feed string for all 'complete' damage reports in the last N minutes."""
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).isoformat()

    docs = list(_container("reports").query_items(
        query=(
            "SELECT * FROM c "
            "WHERE c.crisis_event_id = @cid "
            "AND c.damage.level = 'complete' "
            "AND c.submitted_at >= @since"
        ),
        parameters=[
            {"name": "@cid",   "value": crisis_event_id},
            {"name": "@since", "value": since},
        ],
        enable_cross_partition_query=True,
    ))

    alert = Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")
    SubElement(alert, "identifier").text = f"crisis-platform-{crisis_event_id}-{uuid.uuid4().hex[:8]}"
    SubElement(alert, "sender").text = "crisis-platform@wingu.io"
    SubElement(alert, "sent").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    SubElement(alert, "status").text = "Actual"
    SubElement(alert, "msgType").text = "Alert"
    SubElement(alert, "scope").text = "Public"

    for doc in docs:
        coords = doc.get("location", {}).get("coordinates")
        if not coords:
            continue
        lon, lat = coords

        info = SubElement(alert, "info")
        SubElement(info, "language").text = "en"
        SubElement(info, "category").text = "Infra"
        SubElement(info, "event").text = f"Complete structural damage — {doc['damage']['crisis_nature']}"
        SubElement(info, "urgency").text = "Immediate"
        SubElement(info, "severity").text = "Extreme"
        SubElement(info, "certainty").text = "Observed"
        SubElement(info, "onset").text = doc["submitted_at"]
        SubElement(info, "description").text = (
            doc["damage"].get("description_en")
            or f"Complete damage reported at building {doc.get('building_id', 'unknown')}"
        )

        area = SubElement(info, "area")
        SubElement(area, "areaDesc").text = doc.get("building_id") or "Crisis area"
        SubElement(area, "circle").text = f"{lat},{lon} 0.1"

    indent(alert, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(alert, encoding="unicode")
