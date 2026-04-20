import os
from datetime import datetime, timedelta

from azure.cosmos import CosmosClient


def _container():
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    db = client.get_database_client(os.environ["COSMOS_DATABASE"])
    return db.get_container_client("reports")


def is_duplicate(building_id: str, submitted_at: datetime) -> bool:
    """
    Flag as duplicate if the same building_id appears within the configured window.
    Duplicates are stored and flagged — never silently dropped.
    """
    window_seconds = int(os.environ.get("DUPLICATE_WINDOW_SECONDS", "60"))
    window_start = (submitted_at - timedelta(seconds=window_seconds)).isoformat()

    results = _container().query_items(
        query=(
            "SELECT VALUE COUNT(1) FROM c "
            "WHERE c.building_id = @bid AND c.submitted_at > @since"
        ),
        parameters=[
            {"name": "@bid",   "value": building_id},
            {"name": "@since", "value": window_start},
        ],
        enable_cross_partition_query=True,
    )
    return next(iter(results), 0) > 0
