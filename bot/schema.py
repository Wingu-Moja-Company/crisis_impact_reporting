"""
Schema fetch utilities for the Telegram bot.

Fetches the dynamic form schema from the pipeline API and stores it in
user_data for the duration of the conversation. Falls back to a minimal
hardcoded schema if the API is unreachable.
"""

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)


def _api_base() -> str:
    return os.environ.get("API_BASE_URL", "http://localhost:7071/api")


def _ingest_key() -> str:
    return os.environ.get("INGEST_API_KEY", "")


# ---------------------------------------------------------------------------
# Fallback schema — used when the API is unreachable
# ---------------------------------------------------------------------------

# Minimal schema with just the two mandatory system fields.
# Coordinators can always update the full schema via the admin API.
_FALLBACK_SCHEMA: dict = {
    "version": None,
    "system_fields": {
        "damage_level": {
            "values_locked": True,
            "type": "select",
            "labels": {
                "en": "What is the damage level?",
                "fr": "Quel est le niveau de dommages ?",
                "ar": "ما مستوى الضرر؟",
                "sw": "Kiwango cha uharibifu ni kipi?",
                "es": "¿Cuál es el nivel de daño?",
                "zh": "损坏程度如何？",
            },
            "options": {
                "minimal": {
                    "en": "Minimal — structurally sound, cosmetic damage only",
                    "fr": "Minimal — structure solide, dommages cosmétiques",
                    "ar": "أدنى — الهيكل سليم، أضرار شكلية",
                    "sw": "Kidogo — muundo imara",
                    "es": "Mínimo — estructuralmente sólido",
                    "zh": "轻微——结构完好",
                },
                "partial": {
                    "en": "Partial — repairable, remains usable with caution",
                    "fr": "Partiel — réparable, reste utilisable",
                    "ar": "جزئي — قابل للإصلاح",
                    "sw": "Sehemu — inaweza kukarabatiwa",
                    "es": "Parcial — reparable",
                    "zh": "部分——可修复",
                },
                "complete": {
                    "en": "Complete — structurally unsafe or destroyed",
                    "fr": "Complet — dangereux ou détruit",
                    "ar": "كامل — غير آمن هيكلياً",
                    "sw": "Kamili — si salama",
                    "es": "Completo — inseguro o destruido",
                    "zh": "完全——不安全或已毁",
                },
            },
        },
        "infrastructure_type": {
            "values_locked": False,
            "type": "multiselect",
            "min_selections": 1,
            "labels": {
                "en": "What type of infrastructure is affected?",
                "fr": "Quel type d'infrastructure est affecté ?",
                "ar": "ما نوع البنية التحتية المتضررة؟",
                "sw": "Miundombinu ya aina gani imeathiriwa?",
                "es": "¿Qué tipo de infraestructura está afectada?",
                "zh": "哪类基础设施受到影响？",
            },
            "options": [
                {"value": "residential",  "labels": {"en": "🏠 Residential",        "fr": "🏠 Résidentiel",    "ar": "🏠 سكني",    "sw": "🏠 Makazi",      "es": "🏠 Residencial",  "zh": "🏠 住宅"}},
                {"value": "commercial",   "labels": {"en": "🏪 Commercial",         "fr": "🏪 Commercial",    "ar": "🏪 تجاري",   "sw": "🏪 Biashara",    "es": "🏪 Comercial",    "zh": "🏪 商业"}},
                {"value": "government",   "labels": {"en": "🏛 Government",         "fr": "🏛 Gouvernement",  "ar": "🏛 حكومي",   "sw": "🏛 Serikali",    "es": "🏛 Gobierno",     "zh": "🏛 政府"}},
                {"value": "utility",      "labels": {"en": "⚡ Utility",            "fr": "⚡ Services",      "ar": "⚡ مرافق",   "sw": "⚡ Huduma",      "es": "⚡ Servicios",    "zh": "⚡ 公用设施"}},
                {"value": "transport",    "labels": {"en": "🛣 Transport",          "fr": "🛣 Transport",     "ar": "🛣 نقل",     "sw": "🛣 Usafiri",     "es": "🛣 Transporte",   "zh": "🛣 交通"}},
                {"value": "community",    "labels": {"en": "🏫 Community",          "fr": "🏫 Communauté",   "ar": "🏫 مجتمعي",  "sw": "🏫 Jamii",       "es": "🏫 Comunidad",    "zh": "🏫 社区"}},
                {"value": "public_space", "labels": {"en": "🏟 Public space",       "fr": "🏟 Espace public", "ar": "🏟 فضاء عام", "sw": "🏟 Nafasi ya umma", "es": "🏟 Espacio público", "zh": "🏟 公共空间"}},
                {"value": "other",        "labels": {"en": "❓ Other",             "fr": "❓ Autre",         "ar": "❓ أخرى",    "sw": "❓ Nyingine",    "es": "❓ Otro",         "zh": "❓ 其他"}},
            ],
        },
    },
    "custom_fields": [],
    "_fallback": True,
}


def fallback_schema() -> dict:
    """Return a copy of the minimal hardcoded fallback schema."""
    return dict(_FALLBACK_SCHEMA)


# ---------------------------------------------------------------------------
# API fetch
# ---------------------------------------------------------------------------

def fetch_schema(crisis_event_id: str) -> dict:
    """
    Fetch the current schema for the crisis event from the pipeline API.
    Returns the schema dict on success, or the fallback schema on failure.
    Non-blocking in the sense that all errors are caught — the bot must never
    crash because the schema API is unreachable.
    """
    url = f"{_api_base()}/v1/crisis-events/{crisis_event_id}/schema"
    headers = {}
    if key := _ingest_key():
        headers["X-API-Key"] = key

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            schema = json.loads(resp.read())
        logger.info(
            "Schema fetched for %s v%s (%d custom fields)",
            crisis_event_id,
            schema.get("version"),
            len(schema.get("custom_fields", [])),
        )
        return schema
    except Exception as exc:
        logger.warning(
            "Schema fetch failed for %s (%s: %s) — using fallback",
            crisis_event_id, type(exc).__name__, exc,
        )
        return fallback_schema()
