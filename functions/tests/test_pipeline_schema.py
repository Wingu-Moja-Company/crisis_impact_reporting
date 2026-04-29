"""
Unit tests for the schema-aware pipeline changes.

Tests cover:
- DamageReportSubmission helper methods (get_crisis_nature, get_requires_debris_clearing,
  get_effective_responses)
- Backward compatibility with legacy modular_fields and top-level crisis_nature

Run:
    cd functions
    pytest tests/test_pipeline_schema.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingest.schema import DamageLevel, DamageReportSubmission  # noqa: E402


# ---------------------------------------------------------------------------
# DamageReportSubmission model tests
# ---------------------------------------------------------------------------

class TestDamageReportSubmission:

    def _submission(self, **kwargs) -> DamageReportSubmission:
        """Build a minimal valid submission, merging kwargs."""
        defaults = {
            "damage_level": DamageLevel.PARTIAL,
            "infrastructure_types": ["residential"],
            "crisis_event_id": "ke-flood-dev",
            "channel": "pwa",
            # Location is required by the validator — use a description for unit tests
            "location_description": "Near test market",
        }
        defaults.update(kwargs)
        return DamageReportSubmission(**defaults)

    # ── get_crisis_nature ──────────────────────────────────────────────────

    def test_get_crisis_nature_from_responses(self):
        """Reads crisis_nature from responses dict (new format)."""
        sub = self._submission(
            schema_version=2,
            responses={"crisis_nature": "earthquake"},
        )
        assert sub.get_crisis_nature() == "earthquake"

    def test_get_crisis_nature_from_legacy_field(self):
        """Falls back to top-level crisis_nature (old format)."""
        sub = self._submission(crisis_nature="flood")
        assert sub.get_crisis_nature() == "flood"

    def test_get_crisis_nature_responses_wins_over_legacy(self):
        """responses.crisis_nature takes precedence over top-level crisis_nature."""
        sub = self._submission(
            crisis_nature="flood",
            responses={"crisis_nature": "earthquake"},
        )
        assert sub.get_crisis_nature() == "earthquake"

    def test_get_crisis_nature_returns_none_when_absent(self):
        """Returns None when crisis_nature is not set anywhere."""
        sub = self._submission()
        assert sub.get_crisis_nature() is None

    # ── get_requires_debris_clearing ──────────────────────────────────────

    def test_get_requires_debris_from_responses(self):
        """Reads requires_debris_clearing from responses dict."""
        sub = self._submission(responses={"requires_debris_clearing": True})
        assert sub.get_requires_debris_clearing() is True

    def test_get_requires_debris_from_legacy_field(self):
        """Falls back to top-level requires_debris_clearing."""
        sub = self._submission(requires_debris_clearing=True)
        assert sub.get_requires_debris_clearing() is True

    def test_get_requires_debris_defaults_false(self):
        """Returns False when not set anywhere."""
        sub = self._submission()
        assert sub.get_requires_debris_clearing() is False

    def test_get_requires_debris_string_true_in_responses(self):
        """Handles stringified boolean 'true' from multipart form."""
        sub = self._submission(responses={"requires_debris_clearing": "true"})
        assert sub.get_requires_debris_clearing() is True

    def test_get_requires_debris_string_false_in_responses(self):
        """Handles stringified boolean 'false' from multipart form."""
        sub = self._submission(responses={"requires_debris_clearing": "false"})
        assert sub.get_requires_debris_clearing() is False

    # ── get_effective_responses ────────────────────────────────────────────

    def test_get_effective_responses_returns_responses(self):
        """Returns responses dict for new reports."""
        sub = self._submission(
            schema_version=2,
            responses={"water_level": "knee", "crisis_nature": "flood"},
        )
        responses = sub.get_effective_responses()
        assert responses["water_level"] == "knee"
        assert responses["crisis_nature"] == "flood"

    def test_get_effective_responses_falls_back_to_modular_fields(self):
        """Returns modular_fields for legacy reports."""
        sub = self._submission(
            modular_fields={"electricity_status": "none", "health_services": "unavailable"},
        )
        responses = sub.get_effective_responses()
        assert responses["electricity_status"] == "none"
        assert responses["health_services"] == "unavailable"

    def test_get_effective_responses_includes_legacy_crisis_nature(self):
        """Merges top-level crisis_nature into effective responses for old reports."""
        sub = self._submission(
            crisis_nature="flood",
            requires_debris_clearing=True,
        )
        responses = sub.get_effective_responses()
        assert responses.get("crisis_nature") == "flood"
        assert responses.get("requires_debris_clearing") is True

    def test_get_effective_responses_empty_for_bare_submission(self):
        """Returns dict (possibly empty) for a submission with no custom fields."""
        sub = self._submission()
        responses = sub.get_effective_responses()
        assert isinstance(responses, dict)

    # ── DamageLevel enum validation ───────────────────────────────────────

    def test_invalid_damage_level_raises(self):
        """Invalid damage level raises a validation error."""
        with pytest.raises(Exception):
            DamageReportSubmission(
                damage_level="catastrophic",  # type: ignore
                infrastructure_types=["residential"],
                crisis_event_id="ke-flood-dev",
                channel="pwa",
            )

    def test_empty_infrastructure_types_raises(self):
        """Empty infrastructure_types raises a validation error."""
        with pytest.raises(Exception):
            DamageReportSubmission(
                damage_level=DamageLevel.PARTIAL,
                infrastructure_types=[],  # must be non-empty
                crisis_event_id="ke-flood-dev",
                channel="pwa",
            )

    def test_infrastructure_types_accepts_custom_string(self):
        """infrastructure_types accepts any string now (no enum restriction)."""
        sub = self._submission(infrastructure_types=["custom_type_xyz"])
        assert sub.infrastructure_types == ["custom_type_xyz"]

    def test_schema_version_optional(self):
        """schema_version is optional (None for pre-schema reports)."""
        sub = self._submission()
        assert sub.schema_version is None

    def test_responses_optional(self):
        """responses is optional (defaults to None)."""
        sub = self._submission()
        assert sub.responses is None


# ---------------------------------------------------------------------------
# Export / GeoJSON build_feature backward compatibility
# ---------------------------------------------------------------------------

class TestBuildFeatureBackwardCompat:
    """Ensure build_feature handles both old and new doc formats."""

    def _call_build_feature(self, doc):
        from unittest.mock import patch
        # _photo_url requires Azure credentials — patch it out
        with patch("export.geojson._photo_url", return_value=None):
            from export.geojson import build_feature
            return build_feature(doc)

    def _minimal_doc(self, **kwargs) -> dict:
        doc = {
            "id": "rpt_001",
            "crisis_event_id": "ke-flood-dev",
            "submitted_at": "2026-01-01T00:00:00Z",
            "channel": "pwa",
            "location": {"coordinates": [36.86, -1.26]},
            "damage": {"level": "partial", "infrastructure_types": ["residential"]},
        }
        doc.update(kwargs)
        return doc

    def test_old_format_modular_fields(self):
        """Old reports with modular_fields are exported correctly."""
        doc = self._minimal_doc(
            modular_fields={"electricity_status": "none", "crisis_nature": "flood"},
            damage={"level": "minimal", "infrastructure_types": ["commercial"],
                    "crisis_nature": "flood", "requires_debris_clearing": False},
        )
        feature = self._call_build_feature(doc)
        assert feature is not None
        props = feature["properties"]
        assert props["damage_level"] == "minimal"
        assert props["electricity_status"] == "none"

    def test_new_format_responses(self):
        """New reports with responses dict are exported correctly."""
        doc = self._minimal_doc(
            schema_version=2,
            responses={"crisis_nature": "flood", "water_level": "knee", "requires_debris_clearing": True},
            damage={"level": "complete", "infrastructure_types": ["road"]},
        )
        feature = self._call_build_feature(doc)
        assert feature is not None
        props = feature["properties"]
        assert props["schema_version"] == 2
        assert props["water_level"] == "knee"
        assert props["crisis_nature"] == "flood"

    def test_crisis_nature_backward_compat(self):
        """crisis_nature read from damage.crisis_nature when no responses."""
        doc = self._minimal_doc(
            damage={"level": "partial", "infrastructure_types": ["road"], "crisis_nature": "earthquake"},
        )
        feature = self._call_build_feature(doc)
        assert feature["properties"]["crisis_nature"] == "earthquake"

    def test_requires_debris_backward_compat(self):
        """requires_debris_clearing read from damage when no responses."""
        doc = self._minimal_doc(
            damage={"level": "partial", "infrastructure_types": ["residential"],
                    "requires_debris_clearing": True},
        )
        feature = self._call_build_feature(doc)
        assert feature["properties"]["requires_debris_clearing"] is True

    def test_feature_without_coordinates_returns_none(self):
        """build_feature returns None when no coordinates."""
        doc = self._minimal_doc()
        doc["location"] = {}  # no coordinates
        feature = self._call_build_feature(doc)
        assert feature is None

    def test_responses_flattened_into_properties(self):
        """All keys in responses dict appear as top-level GeoJSON properties."""
        doc = self._minimal_doc(
            responses={
                "crisis_nature": "flood",
                "water_level": "knee",
                "electricity_status": "none",
                "pressing_needs": ["food_water", "shelter"],
            },
            schema_version=1,
        )
        feature = self._call_build_feature(doc)
        props = feature["properties"]
        assert props["water_level"] == "knee"
        assert props["electricity_status"] == "none"
        assert isinstance(props["pressing_needs"], list)
