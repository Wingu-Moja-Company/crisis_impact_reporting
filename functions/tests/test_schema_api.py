"""
Unit tests for functions/schema/service.py and functions/schema/handlers.py.

All Cosmos DB calls are mocked — no Azure credentials required.
Azure SDK stubs are injected by conftest.py before this module loads.

Run:
    cd functions
    pytest tests/test_schema_api.py -v
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force schema submodules to be importable as attributes (conftest stubs azure first)
import importlib
import schema.service   # noqa: F401  — registers schema.service in sys.modules
import schema.handlers  # noqa: F401  — registers schema.handlers in sys.modules
import schema.defaults  # noqa: F401


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _events_mock(doc=None, raise_not_found=False):
    """Return a mock Cosmos container for the crisis_events container."""
    m = MagicMock()
    if raise_not_found:
        from azure.cosmos import exceptions as _exc
        m.read_item.side_effect = _exc.CosmosResourceNotFoundError()
    elif doc is not None:
        m.read_item.return_value = doc
    return m


def _schemas_mock(docs=None, raise_not_found=False):
    """Return a mock Cosmos container for the schemas container."""
    m = MagicMock()
    if raise_not_found:
        from azure.cosmos import exceptions as _exc
        m.read_item.side_effect = _exc.CosmosResourceNotFoundError()
    elif docs is not None:
        m.read_item.return_value = docs[0] if docs else None
        m.query_items.return_value = iter(docs)
    return m


# ---------------------------------------------------------------------------
# Schema service tests
# ---------------------------------------------------------------------------

class TestSchemaService:
    """Test schema.service functions with mocked Cosmos DB."""

    # ── get_current_schema ──────────────────────────────────────────────────

    def test_get_current_schema_returns_none_when_event_missing(self):
        """Returns None when crisis event does not exist."""
        from schema.service import get_current_schema

        ev = _events_mock(raise_not_found=True)
        with patch("schema.service._events", return_value=ev):
            result = get_current_schema("nonexistent-event")
        assert result is None

    def test_get_current_schema_returns_latest(self):
        """Returns schema when event has current_schema_version pointer."""
        from schema.service import get_current_schema

        schema_doc = {
            "id": "schema_test-event_v1",
            "crisis_event_id": "test-event",
            "version": 1,
            "published_at": "2026-01-01T00:00:00Z",
            "system_fields": {"damage_level": {}, "infrastructure_type": {}},
            "custom_fields": [],
        }
        ev = _events_mock({"id": "test-event", "current_schema_version": 1})
        sc = MagicMock()
        sc.read_item.return_value = schema_doc

        with patch("schema.service._events",  return_value=ev), \
             patch("schema.service._schemas", return_value=sc):
            result = get_current_schema("test-event")

        assert result is not None
        assert result["version"] == 1
        assert result["crisis_event_id"] == "test-event"

    # ── get_version_only ────────────────────────────────────────────────────

    def test_get_version_only(self):
        """Returns version number from crisis event doc."""
        from schema.service import get_version_only

        ev = _events_mock({"id": "test-event", "current_schema_version": 3})
        with patch("schema.service._events", return_value=ev):
            result = get_version_only("test-event")
        assert result == 3

    def test_get_version_only_returns_none_when_missing(self):
        """Returns None when crisis event does not exist."""
        from schema.service import get_version_only

        ev = _events_mock(raise_not_found=True)
        with patch("schema.service._events", return_value=ev):
            result = get_version_only("test-event")
        assert result is None

    # ── publish_schema ──────────────────────────────────────────────────────

    def test_publish_schema_increments_version(self):
        """Publish creates version N+1 doc."""
        from schema.service import publish_schema

        # _get_max_version queries schemas; publish then writes to both containers
        sc = MagicMock()
        sc.query_items.return_value = iter([1])   # MAX version returns 1
        sc.upsert_item = MagicMock()

        ev = _events_mock({"id": "test", "current_schema_version": 1})
        ev.upsert_item = MagicMock()

        with patch("schema.service._schemas", return_value=sc), \
             patch("schema.service._events",  return_value=ev):
            body = {"system_fields": {}, "custom_fields": []}
            result = publish_schema("test", body, "admin")

        assert result["version"] == 2
        assert result["crisis_event_id"] == "test"
        assert result["published_by"] == "admin"
        sc.upsert_item.assert_called_once()

    def test_publish_schema_first_version(self):
        """Publish creates v1 when no existing schema."""
        from schema.service import publish_schema

        sc = MagicMock()
        sc.query_items.return_value = iter([None])  # MAX returns None (no docs)
        sc.upsert_item = MagicMock()

        ev = _events_mock(raise_not_found=True)
        ev.upsert_item = MagicMock()

        with patch("schema.service._schemas", return_value=sc), \
             patch("schema.service._events",  return_value=ev):
            body = {"system_fields": {}, "custom_fields": []}
            result = publish_schema("new-event", body, "admin")

        assert result["version"] == 1

    # ── list_schema_history ─────────────────────────────────────────────────

    def test_list_schema_history(self):
        """Returns list of version metadata with custom_field_count."""
        from schema.service import list_schema_history

        docs = [
            {
                "id": "schema_test_v1", "crisis_event_id": "test",
                "version": 1, "published_at": "2026-01-01T00:00:00Z",
                "published_by": "admin", "custom_fields": [],
            },
            {
                "id": "schema_test_v2", "crisis_event_id": "test",
                "version": 2, "published_at": "2026-01-02T00:00:00Z",
                "published_by": "admin", "custom_fields": [{"id": "water_level"}],
            },
        ]
        sc = MagicMock()
        sc.query_items.return_value = iter(docs)
        with patch("schema.service._schemas", return_value=sc):
            result = list_schema_history("test")

        assert len(result) == 2
        assert result[0]["version"] == 1
        assert result[0]["custom_field_count"] == 0
        assert result[1]["custom_field_count"] == 1

    # ── seed_schema ─────────────────────────────────────────────────────────

    def test_seed_schema_is_idempotent(self):
        """seed_schema returns None (skips) if a schema already exists."""
        from schema.service import seed_schema

        sc = MagicMock()
        sc.query_items.return_value = iter([1])  # MAX version = 1 → already seeded
        sc.upsert_item = MagicMock()

        with patch("schema.service._schemas", return_value=sc):
            result = seed_schema("test", {"system_fields": {}, "custom_fields": []})

        # Should return None (idempotent — no new doc written)
        assert result is None
        sc.upsert_item.assert_not_called()

    def test_seed_schema_creates_v1_when_empty(self):
        """seed_schema creates v1 when no schema exists."""
        from schema.service import seed_schema

        sc = MagicMock()
        sc.query_items.return_value = iter([None])  # no existing schema
        sc.upsert_item = MagicMock()

        ev = _events_mock(raise_not_found=True)

        with patch("schema.service._schemas", return_value=sc), \
             patch("schema.service._events",  return_value=ev):
            result = seed_schema("new-event", {"system_fields": {}, "custom_fields": []})

        assert result is not None
        assert result["version"] == 1
        sc.upsert_item.assert_called_once()


# ---------------------------------------------------------------------------
# Schema defaults tests
# ---------------------------------------------------------------------------

class TestSchemaDefaults:
    """Test schema.defaults module."""

    def test_get_default_schema_flood(self):
        """Flood schema has expected custom fields."""
        from schema.defaults import get_default_schema

        schema = get_default_schema("flood")
        assert schema is not None
        assert "system_fields" in schema
        assert "custom_fields" in schema

        # Should include standard flood fields
        field_ids = [f["id"] for f in schema["custom_fields"]]
        assert "crisis_nature" in field_ids
        assert "requires_debris_clearing" in field_ids

    def test_get_default_schema_all_system_labels_en(self):
        """All system field labels have English translation."""
        from schema.defaults import get_default_schema

        for nature in ["flood", "earthquake", "conflict", "generic"]:
            schema = get_default_schema(nature)
            dl = schema["system_fields"]["damage_level"]
            assert dl["labels"].get("en"), f"Missing damage_level label for {nature}"

    def test_get_default_schema_custom_fields_have_labels(self):
        """Every custom field has at least an English label."""
        from schema.defaults import get_default_schema

        schema = get_default_schema("flood")
        for field in schema["custom_fields"]:
            assert field["labels"].get("en"), f"Missing English label for {field['id']}"

    def test_get_default_schema_unknown_falls_back_to_generic(self):
        """Unknown crisis nature returns a valid (generic) schema."""
        from schema.defaults import get_default_schema

        schema = get_default_schema("zombie_apocalypse")
        assert schema is not None
        assert "system_fields" in schema
        assert "custom_fields" in schema

    def test_system_fields_structure(self):
        """SYSTEM_FIELDS export has both required keys."""
        from schema.defaults import SYSTEM_FIELDS

        assert "damage_level" in SYSTEM_FIELDS
        assert "infrastructure_type" in SYSTEM_FIELDS
        assert "options" in SYSTEM_FIELDS["damage_level"]
        # Damage level values must be the fixed trio
        options = SYSTEM_FIELDS["damage_level"]["options"]
        assert set(options.keys()) == {"minimal", "partial", "complete"}


# ---------------------------------------------------------------------------
# Schema handlers (HTTP layer) tests
# ---------------------------------------------------------------------------

class TestSchemaHandlers:
    """Test HTTP handlers with mocked service functions."""

    def _make_request(self, params=None, body=None, method="GET", headers=None, event_id="test"):
        req = MagicMock()
        req.method = method
        req.params = params or {}
        req.headers = headers or {}
        req.route_params = {"event_id": event_id}
        req.get_json.return_value = body
        return req

    @patch("schema.handlers.get_current_schema")
    def test_get_schema_returns_current(self, mock_get):
        """GET without version param returns current schema."""
        from schema.handlers import get_schema

        mock_get.return_value = {
            "version": 1, "crisis_event_id": "test",
            "system_fields": {}, "custom_fields": [],
        }
        req = self._make_request()
        resp = get_schema(req)

        assert resp.status_code == 200
        data = json.loads(resp.get_body())
        assert data["version"] == 1

    @patch("schema.handlers.get_current_schema")
    def test_get_schema_returns_404_when_missing(self, mock_get):
        """GET returns 404 when no schema exists."""
        from schema.handlers import get_schema

        mock_get.return_value = None
        req = self._make_request(event_id="missing-event")
        resp = get_schema(req)
        assert resp.status_code == 404

    @patch("schema.handlers.get_version_only")
    def test_get_schema_version_only(self, mock_ver):
        """GET ?version_only=true returns just the version number."""
        from schema.handlers import get_schema

        mock_ver.return_value = 3
        req = self._make_request(params={"version_only": "true"})
        resp = get_schema(req)
        assert resp.status_code == 200
        data = json.loads(resp.get_body())
        assert data == {"version": 3}

    @patch("schema.handlers.publish_schema")
    def test_post_schema_requires_admin_key(self, mock_publish):
        """POST without admin key returns 403."""
        from schema.handlers import post_schema
        import os as _os

        with patch.dict(_os.environ, {"ADMIN_API_KEY": "secret"}):
            req = self._make_request(method="POST", body={"system_fields": {}, "custom_fields": []})
            req.headers = {}
            resp = post_schema(req)
        assert resp.status_code == 403
        mock_publish.assert_not_called()

    @patch("schema.handlers.publish_schema")
    def test_post_schema_publishes_with_valid_key(self, mock_publish):
        """POST with valid admin key calls publish_schema."""
        from schema.handlers import post_schema
        import os as _os

        mock_publish.return_value = {
            "version": 2, "crisis_event_id": "test",
            "custom_fields": [], "system_fields": {},
        }
        with patch.dict(_os.environ, {"ADMIN_API_KEY": "secret"}):
            req = self._make_request(
                method="POST",
                body={"system_fields": {}, "custom_fields": []},
                headers={"X-Admin-Key": "secret"},
            )
            resp = post_schema(req)
        assert resp.status_code == 201
        mock_publish.assert_called_once()
