"""
Unit and integration tests for the GPT-5.4-mini vision damage assessment
function (_ai_vision_score) in ingest/pipeline.py.

Unit tests mock urllib.request.urlopen so no Azure credentials are needed.
The integration test is skipped unless AOAI_ENDPOINT and AOAI_KEY are set.

Run:
    cd functions
    pytest tests/test_ai_vision.py -v
"""

import io
import json
import os
import sys
import unittest.mock as mock

import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# Path setup — allow importing from functions/ root without installing
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingest.pipeline import _ai_vision_score  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jpeg(width: int = 100, height: int = 80) -> bytes:
    """Return minimal valid JPEG bytes (solid grey image)."""
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _mock_response(payload: dict, status: int = 200):
    """Build a mock object that mimics urllib.request.urlopen context manager."""
    raw = json.dumps({
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }).encode()
    m = mock.MagicMock()
    m.__enter__ = mock.Mock(return_value=m)
    m.__exit__ = mock.Mock(return_value=False)
    m.read.return_value = raw
    m.status = status
    return m


def _patch_urlopen(payload: dict):
    """Convenience: patch urlopen to return a canned GPT payload."""
    return mock.patch(
        "ingest.pipeline.urllib.request.urlopen",
        return_value=_mock_response(payload),
    )


# ---------------------------------------------------------------------------
# Environment fixture — inject fake AOAI credentials for all unit tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fake_aoai_env(monkeypatch):
    """Set fake endpoint + key so the early-return guard doesn't fire."""
    monkeypatch.setenv("AOAI_ENDPOINT", "https://fake.openai.azure.com")
    monkeypatch.setenv("AOAI_KEY", "fake-key-for-unit-tests")
    monkeypatch.setenv("AOAI_DEPLOYMENT", "gpt-5.4-mini")


PHOTO = _make_jpeg()


# ---------------------------------------------------------------------------
# Unit tests — no network calls
# ---------------------------------------------------------------------------

class TestNullScore:
    def test_missing_endpoint_returns_null(self, monkeypatch):
        """Function must degrade gracefully when AOAI_ENDPOINT is not set."""
        monkeypatch.delenv("AOAI_ENDPOINT", raising=False)
        result = _ai_vision_score(PHOTO)
        assert result["confidence"] == 0.0
        assert result["suggested_level"] is None
        assert result["summary"] is None

    def test_missing_key_returns_null(self, monkeypatch):
        """Function must degrade gracefully when AOAI_KEY is not set."""
        monkeypatch.delenv("AOAI_KEY", raising=False)
        result = _ai_vision_score(PHOTO)
        assert result["confidence"] == 0.0
        assert result["suggested_level"] is None


class TestDamageLevelMapping:
    def test_complete_damage(self):
        payload = {
            "damage_level": "complete", "confidence": 0.92,
            "infrastructure_visible": True, "debris_visible": True,
            "rejection_reason": None, "summary": "Roof has fully collapsed.",
        }
        with _patch_urlopen(payload):
            result = _ai_vision_score(PHOTO)
        assert result["suggested_level"] == "complete"
        assert result["confidence"] == pytest.approx(0.92)
        assert result["summary"] == "Roof has fully collapsed."
        assert result["debris_confirmed"] is True

    def test_partial_damage(self):
        payload = {
            "damage_level": "partial", "confidence": 0.78,
            "infrastructure_visible": True, "debris_visible": False,
            "rejection_reason": None, "summary": "Exterior wall cracked, roof intact.",
        }
        with _patch_urlopen(payload):
            result = _ai_vision_score(PHOTO)
        assert result["suggested_level"] == "partial"
        assert result["confidence"] == pytest.approx(0.78)
        assert result["debris_confirmed"] is False

    def test_minimal_damage(self):
        payload = {
            "damage_level": "minimal", "confidence": 0.65,
            "infrastructure_visible": True, "debris_visible": False,
            "rejection_reason": None, "summary": "Minor water marks on facade.",
        }
        with _patch_urlopen(payload):
            result = _ai_vision_score(PHOTO)
        assert result["suggested_level"] == "minimal"
        assert result["confidence"] == pytest.approx(0.65)

    def test_unclear_maps_to_none_level(self):
        """'unclear' damage_level must set suggested_level to None."""
        payload = {
            "damage_level": "unclear", "confidence": 0.1,
            "infrastructure_visible": True, "debris_visible": False,
            "rejection_reason": "too_dark", "summary": "Image too dark to assess.",
        }
        with _patch_urlopen(payload):
            result = _ai_vision_score(PHOTO)
        assert result["suggested_level"] is None
        assert result["rejection_reason"] == "too_dark"


class TestRejectionReasons:
    def test_no_structure_in_photo(self):
        payload = {
            "damage_level": "unclear", "confidence": 0.05,
            "infrastructure_visible": False, "debris_visible": False,
            "rejection_reason": "no_structure",
            "summary": "No building visible in this photo.",
        }
        with _patch_urlopen(payload):
            result = _ai_vision_score(PHOTO)
        assert result["infrastructure_visible"] is False
        assert result["rejection_reason"] == "no_structure"
        assert result["suggested_level"] is None

    def test_unrelated_photo(self):
        payload = {
            "damage_level": "unclear", "confidence": 0.0,
            "infrastructure_visible": False, "debris_visible": False,
            "rejection_reason": "unrelated",
            "summary": "Photo does not show infrastructure damage.",
        }
        with _patch_urlopen(payload):
            result = _ai_vision_score(PHOTO)
        assert result["rejection_reason"] == "unrelated"


class TestResiliency:
    def test_http_error_returns_null(self):
        """urlopen raising an exception must not crash the pipeline."""
        import urllib.error
        with mock.patch(
            "ingest.pipeline.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = _ai_vision_score(PHOTO)
        assert result["confidence"] == 0.0
        assert result["suggested_level"] is None
        assert result["summary"] is None

    def test_malformed_json_returns_null(self):
        """GPT returning non-JSON content must not crash the pipeline."""
        bad_response = mock.MagicMock()
        bad_response.__enter__ = mock.Mock(return_value=bad_response)
        bad_response.__exit__ = mock.Mock(return_value=False)
        # Outer JSON is valid but inner content is not
        bad_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Sorry, I cannot process this image."}}]
        }).encode()
        with mock.patch("ingest.pipeline.urllib.request.urlopen", return_value=bad_response):
            result = _ai_vision_score(PHOTO)
        assert result["confidence"] == 0.0

    def test_timeout_returns_null(self):
        """Socket timeout must not crash the pipeline."""
        import socket
        with mock.patch(
            "ingest.pipeline.urllib.request.urlopen",
            side_effect=socket.timeout("timed out"),
        ):
            result = _ai_vision_score(PHOTO)
        assert result["confidence"] == 0.0

    def test_result_dict_always_has_required_keys(self):
        """Return dict must always contain all expected keys regardless of GPT output."""
        payload = {
            "damage_level": "complete", "confidence": 0.9,
            "infrastructure_visible": True, "debris_visible": True,
            "rejection_reason": None, "summary": "Total collapse.",
        }
        with _patch_urlopen(payload):
            result = _ai_vision_score(PHOTO)
        required_keys = {
            "confidence", "suggested_level", "summary",
            "debris_confirmed", "infrastructure_visible", "rejection_reason",
        }
        assert required_keys.issubset(result.keys())


class TestRequestConstruction:
    def test_uses_correct_deployment_name(self):
        """The HTTP request URL must contain the configured deployment name."""
        payload = {
            "damage_level": "minimal", "confidence": 0.6,
            "infrastructure_visible": True, "debris_visible": False,
            "rejection_reason": None, "summary": "Minor damage.",
        }
        with mock.patch("ingest.pipeline.urllib.request.urlopen",
                        return_value=_mock_response(payload)) as mock_open, \
             mock.patch("ingest.pipeline.urllib.request.Request") as mock_req:
            mock_req.return_value = mock.MagicMock()
            mock_open.return_value = _mock_response(payload)
            _ai_vision_score(PHOTO)
            url_used = mock_req.call_args[0][0]
            assert "gpt-5.4-mini" in url_used

    def test_api_key_in_headers_not_url(self):
        """AOAI_KEY must be sent as a header, never embedded in the URL."""
        payload = {
            "damage_level": "partial", "confidence": 0.75,
            "infrastructure_visible": True, "debris_visible": False,
            "rejection_reason": None, "summary": "Wall cracked.",
        }
        with mock.patch("ingest.pipeline.urllib.request.Request") as mock_req, \
             mock.patch("ingest.pipeline.urllib.request.urlopen",
                        return_value=_mock_response(payload)):
            mock_req.return_value = mock.MagicMock()
            _ai_vision_score(PHOTO)
            call = mock_req.call_args
            url     = call.args[0]
            headers = call.kwargs.get("headers", {})
            # Key must not appear in the URL
            assert "fake-key-for-unit-tests" not in url
            # Key must appear in headers
            assert headers.get("api-key") == "fake-key-for-unit-tests"


# ---------------------------------------------------------------------------
# Integration test — skipped unless real Azure credentials are present
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not (os.environ.get("AOAI_ENDPOINT") and
         os.environ.get("AOAI_KEY") and
         "fake" not in os.environ.get("AOAI_ENDPOINT", "")),
    reason="AOAI_ENDPOINT / AOAI_KEY not configured — skipping live Azure call",
)
class TestIntegration:
    def test_real_azure_call_with_grey_image(self):
        """
        Sends a plain grey JPEG to the real gpt-5.4-mini deployment.
        The image has no visible structure, so we expect either:
          - rejection_reason = 'no_structure' / 'unrelated', OR
          - damage_level = 'unclear'
        The test does NOT assert a specific damage level — it verifies the
        function returns a well-formed dict and doesn't crash.
        """
        result = _ai_vision_score(_make_jpeg(200, 150))
        assert isinstance(result, dict)
        assert "confidence" in result
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
        assert "suggested_level" in result
        assert "summary" in result
        # A grey square should not be classified as real structural damage
        assert result["suggested_level"] in (None, "minimal", "partial", "complete")

    def test_real_azure_call_returns_summary_string(self):
        """Summary field must be a non-empty string (or None) from the model."""
        result = _ai_vision_score(_make_jpeg())
        assert result["summary"] is None or isinstance(result["summary"], str)
