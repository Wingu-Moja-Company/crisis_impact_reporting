"""
Unit tests for the dynamic-schema export functions:
  - export/geojson.py (already covered partially in test_pipeline_schema.py)
  - export/csv_export.py (_collect_response_keys, export_csv column structure)

All Cosmos DB calls are mocked.

Run:
    cd functions
    pytest tests/test_export_schema.py -v
"""

import io
import csv
import os
import sys
import unittest.mock as mock
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# csv_export helpers
# ---------------------------------------------------------------------------

class TestCollectResponseKeys:
    """Tests for _collect_response_keys internal helper."""

    def test_empty_features_returns_empty(self):
        from export.csv_export import _collect_response_keys

        result = _collect_response_keys([])
        assert result == []

    def test_known_fields_come_first(self):
        """Known response fields precede unknown ones."""
        from export.csv_export import _collect_response_keys, _KNOWN_RESPONSE_FIELDS

        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [36.86, -1.26]},
                "properties": {
                    "report_id": "rpt_001",
                    "submitted_at": "2026-01-01T00:00:00Z",
                    "water_level": "knee",
                    "some_custom_field": "value",
                    "crisis_nature": "flood",
                    "requires_debris_clearing": True,
                },
            }
        ]
        result = _collect_response_keys(features)
        # water_level is in _KNOWN_RESPONSE_FIELDS — should come first
        assert "water_level" in result
        assert "some_custom_field" in result
        # crisis_nature and requires_debris_clearing are in _CORE_FIELDS, so excluded
        assert "crisis_nature" not in result
        assert "requires_debris_clearing" not in result
        # Known fields before custom
        wi = result.index("water_level")
        si = result.index("some_custom_field")
        assert wi < si

    def test_deduplication(self):
        """Each key appears once even across multiple features."""
        from export.csv_export import _collect_response_keys

        features = [
            {"properties": {"water_level": "knee", "electricity_status": "none"}},
            {"properties": {"water_level": "waist", "health_services": "limited"}},
        ]
        result = _collect_response_keys(features)
        assert result.count("water_level") == 1
        assert "electricity_status" in result
        assert "health_services" in result


class TestExportCSV:
    """Tests for export_csv output structure."""

    def _mock_geojson_collection(self, features: list[dict]) -> dict:
        return {"type": "FeatureCollection", "features": features}

    def _minimal_feature(self, extra_props: dict | None = None) -> dict:
        props = {
            "report_id": "rpt_001",
            "crisis_event_id": "ke-flood-dev",
            "submitted_at": "2026-01-01T00:00:00Z",
            "channel": "pwa",
            "schema_version": 2,
            "damage_level": "partial",
            "infrastructure_types": ["residential"],
            "crisis_nature": "flood",
            "requires_debris_clearing": False,
            "description_en": None,
            "ai_vision_confidence": None,
            "ai_vision_suggested_level": None,
            "ai_vision_summary": None,
            "ai_vision_access_status": None,
            "ai_vision_intervention_priority": None,
            "what3words": None,
            "location_description": None,
            "building_footprint_matched": False,
            "submitter_tier": "public",
        }
        if extra_props:
            props.update(extra_props)
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [36.86, -1.26]},
            "properties": props,
        }

    @patch("export.csv_export.export_geojson")
    def test_csv_has_core_columns(self, mock_geojson):
        """CSV always contains core field columns."""
        from export.csv_export import export_csv, _CORE_FIELDS

        mock_geojson.return_value = self._mock_geojson_collection([self._minimal_feature()])
        csv_str = export_csv("ke-flood-dev")
        reader = csv.DictReader(io.StringIO(csv_str))
        headers = reader.fieldnames or []
        for field in _CORE_FIELDS:
            assert field in headers, f"Missing core field: {field}"

    @patch("export.csv_export.export_geojson")
    def test_csv_schema_version_column(self, mock_geojson):
        """CSV includes schema_version column."""
        from export.csv_export import export_csv

        mock_geojson.return_value = self._mock_geojson_collection([
            self._minimal_feature({"schema_version": 2})
        ])
        csv_str = export_csv("ke-flood-dev")
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["schema_version"] == "2"

    @patch("export.csv_export.export_geojson")
    def test_csv_dynamic_columns(self, mock_geojson):
        """Dynamic response fields appear as columns in CSV."""
        from export.csv_export import export_csv

        mock_geojson.return_value = self._mock_geojson_collection([
            self._minimal_feature({"water_level": "knee", "electricity_status": "none"}),
        ])
        csv_str = export_csv("ke-flood-dev")
        reader = csv.DictReader(io.StringIO(csv_str))
        headers = reader.fieldnames or []
        assert "water_level" in headers
        assert "electricity_status" in headers

    @patch("export.csv_export.export_geojson")
    def test_csv_list_values_serialised(self, mock_geojson):
        """List-valued fields are JSON-serialised in CSV cells."""
        from export.csv_export import export_csv
        import json

        mock_geojson.return_value = self._mock_geojson_collection([
            self._minimal_feature({"pressing_needs": ["food_water", "shelter"]}),
        ])
        csv_str = export_csv("ke-flood-dev")
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        val = rows[0]["pressing_needs"]
        # Should be a JSON string
        parsed = json.loads(val)
        assert "food_water" in parsed

    @patch("export.csv_export.export_geojson")
    def test_csv_infrastructure_types_joined(self, mock_geojson):
        """infrastructure_types list is comma-joined."""
        from export.csv_export import export_csv

        mock_geojson.return_value = self._mock_geojson_collection([
            self._minimal_feature({"infrastructure_types": ["residential", "commercial"]}),
        ])
        csv_str = export_csv("ke-flood-dev")
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        assert rows[0]["infrastructure_types"] == "residential,commercial"

    @patch("export.csv_export.export_geojson")
    def test_csv_sparse_old_reports(self, mock_geojson):
        """Old reports missing dynamic fields get empty cells (no KeyError)."""
        from export.csv_export import export_csv

        new_report = self._minimal_feature({"water_level": "knee"})
        old_report = self._minimal_feature()  # no water_level

        mock_geojson.return_value = self._mock_geojson_collection([new_report, old_report])
        csv_str = export_csv("ke-flood-dev")
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["water_level"] == "knee"
        assert rows[1]["water_level"] == ""  # sparse — empty for old report

    @patch("export.csv_export.export_geojson")
    def test_csv_empty_collection(self, mock_geojson):
        """Export with no features produces only the header row."""
        from export.csv_export import export_csv

        mock_geojson.return_value = self._mock_geojson_collection([])
        csv_str = export_csv("ke-flood-dev")
        lines = [l for l in csv_str.strip().splitlines() if l]
        assert len(lines) == 1  # just the header

    @patch("export.csv_export.export_geojson")
    def test_csv_lat_lon_columns(self, mock_geojson):
        """Latitude and longitude are separate columns."""
        from export.csv_export import export_csv

        mock_geojson.return_value = self._mock_geojson_collection([self._minimal_feature()])
        csv_str = export_csv("ke-flood-dev")
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        assert rows[0]["latitude"] == "-1.26"
        assert rows[0]["longitude"] == "36.86"
