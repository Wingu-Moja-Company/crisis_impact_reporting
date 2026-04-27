"""
Unit tests for functions/schema/service.py and functions/schema/handlers.py.

All Cosmos DB calls are mocked — no Azure credentials required.

Run:
    cd functions
    pytest tests/test_schema_api.py -v
"""

import json
import os
import sys
import unittest.mock as mock
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Schema service tests
# ---------------------------------------------------------------------------

class TestSchemaService:
    """Test schema.service functions with mocked Cosmos DB."""

    def _make_container_mock(self, docs: list[dict]) -> MagicMock:
        """Return a mock container whose query_items returns docs."""
        container = MagicMock()
        container.query_items.return_value = iter(docs)
        return container

    @patch("schema.service._container")
    def test_get_current_schema_returns_none_when_empty(self, mock_container_fn):
        """Returns None when no schemas exist for a crisis event."""
        from schema.service import get_current_schema

        schemas_mock = self._make_container_mock([])
        events_mock = self._make_container_mock([])

        def container_side_effect(name):
            return schemas_mock if name == "schemas" else events_mock

        mock_container_fn.side_effect = container_side_effect

        result = get_current_schema("nonexistent-event")
        assert result is None

    @patch("schema.service._container")
    def test_get_current_schema_returns_latest(self, mock_container_fn):
        """Returns schema when one exists."""
        from schema.service import get_current_schema

        schema_doc = {
            "id": "schema_test-event_v1",
            "crisis_event_id": "test-event",
            "version": 1,
            "published_at": "2026-01-01T00:00:00Z",
            "system_fields": {"damage_level": {}, "infrastructure_type": {}},
            "custom_fields": [],
        }
        schemas_mock = self._make_container_mock([schema_doc])
        events_mock = self._make_container_mock([
            {"id": "test-event", "current_schema_version": 1}
        ])

        def container_side_effect(name):
            return schemas_mock if name == "schemas" else events_mock

        mock_container_fn.side_effect = container_side_effect

        result = get_current_schema("test-event")
        assert result is not None
        assert result["version"] == 1
        assert result["crisis_event_id"] == "test-event"

    @patch("schema.service._container")
    def test_get_version_only(self, mock_container_fn):
        """Returns version number from crisis event doc."""
        from schema.service import get_version_only

        events_mock = self._make_container_mock([
            {"id": "test-event", "current_schema_version": 3}
        ])
        mock_container_fn.return_value = events_mock

        result = get_version_only("test-event")
        assert result == 3

    @patch("schema.service._container")
    def test_get_version_only_returns_none_when_missing(self, mock_container_fn):
        """Returns None when crisis event has no schema version."""
        from schema.service import get_version_only

        events_mock = self._make_container_mock([{"id": "test-event"}])
        mock_container_fn.return_value = events_mock

        result = get_version_only("test-event")
        assert result is None

    @patch("schema.service._container")
    def test_publish_schema_increments_version(self, mock_container_fn):
        """Publish creates version N+1 doc."""
        from schema.service import publish_schema

        schemas_mock = MagicMock()
        schemas_mock.query_items.return_value = iter([
            {"id": "schema_test_v1", "crisis_event_id": "test", "version": 1}
        ])
        schemas_mock.upsert_item = MagicMock()

        events_mock = MagicMock()
        events_mock.query_items.return_value = iter([
            {"id": "test", "current_schema_version": 1}
        ])
        events_mock.upsert_item = MagicMock()

        def container_side_effect(name):
            return schemas_mock if name == "schemas" else events_mock

        mock_container_fn.side_effect = container_side_effect

        body = {"system_fields": {}, "custom_fields": []}
        result = publish_schema("test", body, "admin")

        assert result["version"] == 2
        assert result["crisis_event_id"] == "test"
        assert result["published_by"] == "admin"
        schemas_mock.upsert_item.assert_called_once()

    @patch("schema.service._container")
    def test_publish_schema_first_version(self, mock_container_fn):
        """Publish creates v1 when no existing schema."""
        from schema.service import publish_schema

        schemas_mock = MagicMock()
        schemas_mock.query_items.return_value = iter([])
        schemas_mock.upsert_item = MagicMock()

        events_mock = MagicMock()
        events_mock.query_items.return_value = iter([])
        events_mock.upsert_item = MagicMock()

        def container_side_effect(name):
            return schemas_mock if name == "schemas" else events_mock

        mock_container_fn.side_effect = container_side_effect

        body = {"system_fields": {}, "custom_fields": []}
        result = publish_schema("new-event", body, "admin")

        assert result["version"] == 1

    @patch("schema.service._container")
    def test_list_schema_history(self, mock_container_fn):
        """Returns list of version metadata."""
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
        schemas_mock = self._make_container_mock(docs)
        mock_container_fn.return_value = schemas_mock

        result = list_schema_history("test")
        assert len(result) == 2
        assert result[0]["version"] == 1
        assert result[1]["custom_field_count"] == 1

    @patch("schema.service._container")
    def test_seed_schema_is_idempotent(self, mock_container_fn):
        """seed_schema skips if a schema already exists."""
        from schema.service import seed_schema

        existing_doc = {
            "id": "schema_test_v1", "crisis_event_id": "test", "version": 1,
        }
        schemas_mock = self._make_container_mock([existing_doc])
        schemas_mock.upsert_item = MagicMock()
        events_mock = self._make_container_mock([
            {"id": "test", "current_schema_version": 1}
        ])

        def container_side_effect(name):
            return schemas_mock if name == "schemas" else events_mock

        mock_container_fn.side_effect = container_side_effect

        result = seed_schema("test", {"system_fields": {}, "custom_fields": []})
        # Should return existing doc, not create new one
        assert result is not None
        schemas_mock.upsert_item.assert_not_called()


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

    def _make_request(self, params: dict | None = None, body: dict | None = None,
                      method: str = "GET", headers: dict | None = None,
                      event_id: str = "test"):
        req = MagicMock()
        req.method = method
        req.params = params or {}
        req.headers = headers or {}
        req.route_params = {"event_id": event_id}
        if body is not None:
            req.get_json.return_value = body
        else:
            req.get_json.return_value = None
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

        mock_publish.return_value = {"version": 2, "crisis_event_id": "test", "custom_fields": [], "system_fields": {}}

        with patch.dict(_os.environ, {"ADMIN_API_KEY": "secret"}):
            req = self._make_request(
                method="POST",
                body={"system_fields": {}, "custom_fields": []},
                headers={"X-Admin-Key": "secret"},
            )
            resp = post_schema(req)
        assert resp.status_code == 201
        mock_publish.assert_called_once()
