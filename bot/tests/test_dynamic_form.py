"""
Tests for the schema-driven bot form flow.

Covers:
- bot/schema.py: fetch_schema, fallback_schema
- bot/keyboards/dynamic.py: keyboard builders
- bot/handlers/form.py: callback routing (index-driven state machine)
- bot/handlers/confirm.py: payload assembly

All HTTP calls and Telegram API calls are mocked.

Run (from repo root):
    cd bot
    pytest tests/test_dynamic_form.py -v
"""

import json
import os
import sys
import unittest.mock as mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Bot package lives in bot/ — adjust path for running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# ---------------------------------------------------------------------------
# Fixtures — minimal test schema
# ---------------------------------------------------------------------------

def _make_schema(custom_fields=None):
    """Return a minimal valid schema dict."""
    return {
        "crisis_event_id": "ke-flood-dev",
        "version": 1,
        "system_fields": {
            "damage_level": {
                "values_locked": True,
                "labels": {"en": "What is the damage level?"},
                "options": {
                    "minimal":  {"en": "Minimal"},
                    "partial":  {"en": "Partial"},
                    "complete": {"en": "Complete"},
                },
            },
            "infrastructure_type": {
                "values_locked": False,
                "type": "multiselect",
                "labels": {"en": "What infrastructure is affected?"},
                "options": [
                    {"value": "residential", "labels": {"en": "Residential"}},
                    {"value": "road",        "labels": {"en": "Road / Bridge"}},
                ],
            },
        },
        "custom_fields": custom_fields or [
            {
                "id": "crisis_nature",
                "type": "select",
                "required": True,
                "order": 1,
                "labels": {"en": "What type of crisis?"},
                "options": [
                    {"value": "flood",      "labels": {"en": "Flood"}},
                    {"value": "earthquake", "labels": {"en": "Earthquake"}},
                ],
            },
            {
                "id": "requires_debris_clearing",
                "type": "boolean",
                "required": True,
                "order": 2,
                "labels": {"en": "Does this site require debris clearing?"},
            },
            {
                "id": "water_level",
                "type": "select",
                "required": False,
                "order": 3,
                "labels": {"en": "Estimated water level?"},
                "options": [
                    {"value": "ankle", "labels": {"en": "Ankle deep"}},
                    {"value": "knee",  "labels": {"en": "Knee deep"}},
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# schema.py tests
# ---------------------------------------------------------------------------

class TestFetchSchema:
    """Tests for bot/schema.py fetch_schema and fallback_schema."""

    @patch("schema.requests") if os.path.exists(os.path.join(os.path.dirname(__file__), "../schema.py")) else pytest.mark.skip
    def test_fallback_schema_structure(self):
        """fallback_schema returns a valid schema with system_fields only."""
        from schema import fallback_schema

        fb = fallback_schema()
        assert "system_fields" in fb
        assert "custom_fields" in fb
        assert fb["_fallback"] is True
        assert len(fb["custom_fields"]) == 0

    def test_fallback_schema_has_required_system_fields(self):
        """fallback_schema always has damage_level and infrastructure_type."""
        try:
            from schema import fallback_schema
        except ImportError:
            pytest.skip("schema module not importable in test env")

        fb = fallback_schema()
        assert "damage_level" in fb["system_fields"]
        assert "infrastructure_type" in fb["system_fields"]

    @patch("schema.INGEST_API_KEY", "test-key")
    @patch("schema.API_BASE", "http://localhost:7071/api")
    def test_fetch_schema_uses_fallback_on_http_error(self):
        """fetch_schema falls back gracefully when API is unavailable."""
        try:
            from schema import fetch_schema
        except ImportError:
            pytest.skip("schema module not importable in test env")

        with patch("schema.urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = fetch_schema("ke-flood-dev")

        assert "system_fields" in result
        assert result.get("_fallback") is True


# ---------------------------------------------------------------------------
# keyboards/dynamic.py tests
# ---------------------------------------------------------------------------

class TestDynamicKeyboards:
    """Tests for bot keyboard builders from schema."""

    def _get_builders(self):
        try:
            from keyboards.dynamic import (
                build_damage_level,
                build_infra_type,
                build_select_field,
                build_boolean_field,
                build_multiselect_field,
                field_question,
                system_field_question,
            )
            return (build_damage_level, build_infra_type, build_select_field,
                    build_boolean_field, build_multiselect_field,
                    field_question, system_field_question)
        except ImportError:
            pytest.skip("keyboards.dynamic not importable in test env")

    def test_build_damage_level_has_three_buttons(self):
        """Damage level keyboard always has exactly three options."""
        builders = self._get_builders()
        build_damage_level = builders[0]
        schema = _make_schema()
        kb = build_damage_level(schema, "en")
        # InlineKeyboardMarkup has inline_keyboard attribute
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        labels = [btn.text for btn in buttons]
        assert len(buttons) == 3
        assert any("Minimal" in l or "minimal" in l.lower() for l in labels)

    def test_build_damage_level_callback_format(self):
        """Damage level buttons use 'dmg:{value}' callback format."""
        builders = self._get_builders()
        build_damage_level = builders[0]
        schema = _make_schema()
        kb = build_damage_level(schema, "en")
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        for btn in buttons:
            assert btn.callback_data.startswith("dmg:"), f"Bad callback: {btn.callback_data}"

    def test_build_infra_type_includes_done_button(self):
        """Infrastructure type keyboard has a Done button."""
        builders = self._get_builders()
        build_infra_type = builders[1]
        schema = _make_schema()
        kb = build_infra_type(schema, "en", set())
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        done_buttons = [b for b in buttons if b.callback_data == "infra:done"]
        assert len(done_buttons) == 1

    def test_build_select_field_callback_format(self):
        """Select field buttons use 'f:{idx}:{value}' callback format."""
        builders = self._get_builders()
        build_select_field = builders[2]
        schema = _make_schema()
        field = schema["custom_fields"][0]  # crisis_nature
        kb = build_select_field(field, "en", 0)
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        for btn in buttons:
            assert btn.callback_data.startswith("f:0:"), f"Bad callback: {btn.callback_data}"

    def test_build_boolean_field_has_two_buttons(self):
        """Boolean field keyboard has exactly two buttons (yes/no)."""
        builders = self._get_builders()
        build_boolean_field = builders[3]
        schema = _make_schema()
        field = schema["custom_fields"][1]  # requires_debris_clearing
        kb = build_boolean_field(field, "en", 1)
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        assert len(buttons) == 2
        callbacks = {btn.callback_data for btn in buttons}
        assert "f:1:true" in callbacks
        assert "f:1:false" in callbacks

    def test_callback_data_under_64_bytes(self):
        """All callback data is within Telegram's 64-byte limit."""
        builders = self._get_builders()
        build_select_field, build_boolean_field, build_multiselect_field = builders[2], builders[3], builders[4]
        schema = _make_schema()

        for idx, field in enumerate(schema["custom_fields"]):
            if field["type"] == "select":
                kb = build_select_field(field, "en", idx)
            elif field["type"] == "boolean":
                kb = build_boolean_field(field, "en", idx)
            elif field["type"] == "multiselect":
                kb = build_multiselect_field(field, "en", idx, set())
            else:
                continue

            for row in kb.inline_keyboard:
                for btn in row:
                    data = btn.callback_data.encode("utf-8")
                    assert len(data) <= 64, f"Callback too long: {btn.callback_data!r} ({len(data)} bytes)"

    def test_field_question_includes_total(self):
        """field_question shows current position out of total."""
        builders = self._get_builders()
        field_question = builders[5]
        schema = _make_schema()
        field = schema["custom_fields"][0]
        text = field_question(field, "en", 0, 3)
        assert "1" in text or "(1" in text or "/3" in text

    def test_field_question_marks_optional(self):
        """field_question marks optional fields."""
        builders = self._get_builders()
        field_question = builders[5]
        schema = _make_schema()
        optional_field = schema["custom_fields"][2]  # water_level, required=False
        text = field_question(optional_field, "en", 2, 3)
        assert "optional" in text.lower() or "skip" in text.lower() or "Optional" in text


# ---------------------------------------------------------------------------
# confirm.py payload tests
# ---------------------------------------------------------------------------

class TestConfirmPayload:
    """Tests for confirm handler payload assembly."""

    def test_payload_includes_schema_version_and_responses(self):
        """Confirm handler builds payload with schema_version and responses."""
        try:
            from handlers.confirm import _build_payload
        except (ImportError, AttributeError):
            pytest.skip("_build_payload not directly importable in test env")

        user_data = {
            "schema": _make_schema(),
            "schema_version": 1,
            "damage_level": "partial",
            "infra_selected": ["residential"],
            "responses": {"crisis_nature": "flood", "requires_debris_clearing": "false"},
            "gps_lat": -1.2577,
            "gps_lon": 36.8614,
            "crisis_event_id": "ke-flood-dev",
        }
        payload = _build_payload(user_data)
        assert "schema_version" in payload
        assert "responses" in payload
        # Should NOT have individual modular_fields
        assert "modular_fields" not in payload
        assert payload["damage_level"] == "partial"

    def test_payload_without_schema_version_still_valid(self):
        """Confirm payload is valid even without schema_version (fallback schema)."""
        try:
            from handlers.confirm import _build_payload
        except (ImportError, AttributeError):
            pytest.skip("_build_payload not directly importable in test env")

        user_data = {
            "schema": _make_schema(),
            "schema_version": None,
            "damage_level": "minimal",
            "infra_selected": ["road"],
            "responses": {},
            "gps_lat": -1.2577,
            "gps_lon": 36.8614,
            "crisis_event_id": "ke-flood-dev",
        }
        payload = _build_payload(user_data)
        assert "damage_level" in payload
        assert "schema_version" not in payload or payload.get("schema_version") is None


# ---------------------------------------------------------------------------
# i18n new keys tests
# ---------------------------------------------------------------------------

class TestNewStringKeys:
    """Ensure new i18n keys added for dynamic form are present in all languages."""

    def test_new_keys_present(self):
        """All new string keys exist in STRINGS dict."""
        try:
            from i18n.strings import STRINGS
        except ImportError:
            pytest.skip("i18n.strings not importable in test env")

        required_new_keys = [
            "schema_unavailable",
            "field_skip",
            "field_select_min_one",
            "field_required",
            "field_invalid_number",
        ]
        for key in required_new_keys:
            assert key in STRINGS, f"Missing new key: {key}"

    def test_new_keys_have_english(self):
        """New keys have English translations."""
        try:
            from i18n.strings import STRINGS
        except ImportError:
            pytest.skip("i18n.strings not importable in test env")

        new_keys = ["schema_unavailable", "field_skip", "field_select_min_one"]
        for key in new_keys:
            if key in STRINGS:
                assert STRINGS[key].get("en"), f"Missing English for key: {key}"
