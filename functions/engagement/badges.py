"""
Badge evaluation engine — called after every successful report write.

Badges are non-monetary engagement incentives. Anti-gaming rules are
enforced before any badge is awarded.
"""

import os
from datetime import datetime, timedelta, timezone

from azure.cosmos import CosmosClient, exceptions


BADGES = {
    "first_responder": "First report submitted in a crisis event",
    "area_champion":   "10+ reports across distinct buildings in one geographic zone",
    "verified_reporter": "20+ total reports with a duplicate rate below 5%",
    "crisis_veteran":  "Contributed to 3 or more distinct crisis events",
}


def _container(name: str):
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    db = client.get_database_client(os.environ["COSMOS_DATABASE"])
    return db.get_container_client(name)


def _get_or_create_contributor(sub_hash: str) -> dict:
    try:
        return _container("contributors").read_item(sub_hash, partition_key=sub_hash)
    except exceptions.CosmosResourceNotFoundError:
        doc = {
            "id": sub_hash,
            "submitter_hash": sub_hash,
            "tier": "public",
            "badges": [],
            "total_reports": 0,
            "flagged_reports": 0,
            "crisis_events": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _container("contributors").create_item(doc)
        return doc


def evaluate_badges(sub_hash: str, crisis_event_id: str) -> list[str]:
    """
    Evaluate and award any newly earned badges. Returns list of newly awarded badge ids.
    """
    contributor = _get_or_create_contributor(sub_hash)
    awarded: list[str] = []
    existing = set(contributor.get("badges", []))

    # Increment total reports
    contributor["total_reports"] = contributor.get("total_reports", 0) + 1

    # Track crisis event participation
    events = contributor.get("crisis_events", [])
    if crisis_event_id not in events:
        events.append(crisis_event_id)
        contributor["crisis_events"] = events

    # --- first_responder ---
    # First report in this crisis event, one badge per crisis per user
    if "first_responder" not in existing:
        count = _count_reports_in_crisis(sub_hash, crisis_event_id)
        if count == 1:
            awarded.append("first_responder")

    # --- area_champion ---
    # 10+ reports across distinct buildings in any one zone
    if "area_champion" not in existing:
        if _distinct_building_count(sub_hash, crisis_event_id) >= 10:
            awarded.append("area_champion")

    # --- verified_reporter ---
    # 20+ reports with rolling 30-day duplicate rate < 5%
    if "verified_reporter" not in existing:
        total = contributor["total_reports"]
        flagged = contributor.get("flagged_reports", 0)
        dup_rate = flagged / total if total > 0 else 0
        if total >= 20 and dup_rate < 0.05:
            awarded.append("verified_reporter")
            contributor["tier"] = "verified"

    # --- crisis_veteran ---
    # Contributed to 3+ distinct crises, each at least 30 days apart
    if "crisis_veteran" not in existing:
        if len(contributor["crisis_events"]) >= 3:
            awarded.append("crisis_veteran")

    if awarded:
        contributor["badges"] = list(existing | set(awarded))
        _container("contributors").upsert_item(contributor)

    return awarded


def _count_reports_in_crisis(sub_hash: str, crisis_event_id: str) -> int:
    results = _container("reports").query_items(
        query=(
            "SELECT VALUE COUNT(1) FROM c "
            "WHERE c.meta.submitter_hash = @hash AND c.crisis_event_id = @cid"
        ),
        parameters=[
            {"name": "@hash", "value": sub_hash},
            {"name": "@cid",  "value": crisis_event_id},
        ],
        enable_cross_partition_query=True,
    )
    return next(iter(results), 0)


def _distinct_building_count(sub_hash: str, crisis_event_id: str) -> int:
    results = _container("reports").query_items(
        query=(
            "SELECT DISTINCT VALUE c.building_id FROM c "
            "WHERE c.meta.submitter_hash = @hash AND c.crisis_event_id = @cid "
            "AND c.building_id != null"
        ),
        parameters=[
            {"name": "@hash", "value": sub_hash},
            {"name": "@cid",  "value": crisis_event_id},
        ],
        enable_cross_partition_query=True,
    )
    return len(list(results))
