"""
Notify all registered partner webhooks that a crisis event has been activated.

Usage:
    python scripts/notify_partners.py --crisis-id ke-flood-2026-04
"""

import argparse
import json
import os
import uuid
import urllib.request
from datetime import datetime, timezone

from azure.cosmos import CosmosClient


def _subscriptions():
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client("partner_subscriptions")


def notify(crisis_event_id: str) -> None:
    subs = list(_subscriptions().query_items("SELECT * FROM c", enable_cross_partition_query=True))
    if not subs:
        print("No partner subscriptions registered.")
        return

    event = {
        "specversion": "1.0",
        "type":        "io.crisisplatform.crisis.activated",
        "source":      f"/crisis-platform/{crisis_event_id}",
        "id":          str(uuid.uuid4()),
        "time":        datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": {"crisis_event_id": crisis_event_id, "status": "active"},
    }
    payload = json.dumps(event).encode()

    for sub in subs:
        url = sub.get("callback_url", "")
        if not url:
            continue
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/cloudevents+json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                print(f"  Notified: {sub.get('partner_id', url)}")
        except Exception as exc:
            print(f"  FAILED:   {sub.get('partner_id', url)} — {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Notify partner webhooks of crisis activation")
    parser.add_argument("--crisis-id", required=True, dest="crisis_id")
    args = parser.parse_args()
    notify(args.crisis_id)


if __name__ == "__main__":
    main()
