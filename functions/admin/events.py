"""
Admin API handlers for crisis event management.
All endpoints require X-Admin-Key header matching ADMIN_API_KEY env var.
"""

import hmac
import json
import os
import re
from datetime import datetime, timezone

import azure.functions as func
from azure.cosmos import CosmosClient, exceptions as cosmos_exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$")

_FORBIDDEN = func.HttpResponse(
    '{"error":"forbidden"}', status_code=403, mimetype="application/json",
)
_BAD_REQUEST = lambda msg: func.HttpResponse(
    json.dumps({"error": msg}), status_code=400, mimetype="application/json",
)
_NOT_FOUND = func.HttpResponse(
    '{"error":"not_found"}', status_code=404, mimetype="application/json",
)


def _check_admin_key(req: func.HttpRequest) -> bool:
    expected = os.environ.get("ADMIN_API_KEY", "")
    if not expected:
        return True  # dev mode — no key required
    provided = req.headers.get("X-Admin-Key", "")
    return bool(provided) and hmac.compare_digest(provided, expected)


def _container(name: str):
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], os.environ["COSMOS_KEY"])
    return client.get_database_client(os.environ["COSMOS_DATABASE"]).get_container_client(name)


# ---------------------------------------------------------------------------
# Schema templates (embedded so Functions deployment is self-contained)
# ---------------------------------------------------------------------------

_UNDP_FIELDS = [
    {
        "id": "electricity_status", "type": "single_select", "required": True,
        "label": {"en": "What is the current condition of electricity infrastructure in your community following the crisis?"},
        "options": [
            {"value": "no_damage",  "label": {"en": "No damage observed"}},
            {"value": "minor",      "label": {"en": "Minor damage (service disruptions but quickly repairable)"}},
            {"value": "moderate",   "label": {"en": "Moderate damage (partial outages requiring repairs)"}},
            {"value": "severe",     "label": {"en": "Severe damage (major infrastructure damaged, prolonged outages)"}},
            {"value": "destroyed",  "label": {"en": "Completely destroyed (no electricity infrastructure functioning)"}},
            {"value": "unknown",    "label": {"en": "Unknown/cannot be assessed"}},
        ],
    },
    {
        "id": "health_services", "type": "single_select", "required": True,
        "label": {"en": "How would you rate the overall functioning of health services in your community since the event?"},
        "options": [
            {"value": "fully_functional",    "label": {"en": "Fully functional"}},
            {"value": "partially_functional","label": {"en": "Partially functional"}},
            {"value": "largely_disrupted",   "label": {"en": "Largely disrupted"}},
            {"value": "not_functioning",     "label": {"en": "Not functioning at all"}},
            {"value": "unknown",             "label": {"en": "Unknown"}},
        ],
    },
    {
        "id": "pressing_needs", "type": "multi_select", "required": True,
        "label": {"en": "What are the most pressing needs?"},
        "options": [
            {"value": "food_water",        "label": {"en": "Food assistance and safe drinking water"}},
            {"value": "cash_financial",    "label": {"en": "Cash or financial assistance"}},
            {"value": "healthcare",        "label": {"en": "Access to healthcare and essential medicines"}},
            {"value": "shelter",           "label": {"en": "Shelter, housing repair, or temporary accommodation"}},
            {"value": "livelihoods",       "label": {"en": "Restoration of livelihoods or income sources"}},
            {"value": "wash",              "label": {"en": "Water, sanitation, and hygiene (toilets, washing facilities)"}},
            {"value": "basic_services",    "label": {"en": "Restoration of basic services and infrastructure (electricity, roads, schools)"}},
            {"value": "protection",        "label": {"en": "Protection services and psychosocial support"}},
            {"value": "community_support", "label": {"en": "Support from local authorities and community organizations"}},
            {"value": "other",             "label": {"en": "Other, please specify"}},
        ],
    },
]

_SCHEMAS: dict[str, dict] = {
    "flood": {
        "crisis_nature": "flood",
        "core_fields": ["damage_level", "infrastructure_types", "crisis_nature",
                        "requires_debris_clearing", "photo", "location"],
        "modular_fields": [
            {
                "id": "water_level", "type": "single_select", "required": True,
                "label": {"en": "Estimated water level at the site",
                          "ar": "مستوى الماء المقدر في الموقع",
                          "fr": "Niveau d'eau estimé sur le site",
                          "zh": "现场估计水位", "ru": "Оценочный уровень воды на объекте",
                          "es": "Nivel de agua estimado en el sitio"},
                "options": [
                    {"value": "ankle",   "label": {"en": "Ankle deep (< 0.5 m)"}},
                    {"value": "knee",    "label": {"en": "Knee deep (0.5–1 m)"}},
                    {"value": "waist",   "label": {"en": "Waist deep (1–2 m)"}},
                    {"value": "above",   "label": {"en": "Above head (> 2 m)"}},
                    {"value": "receded", "label": {"en": "Water has receded"}},
                ],
            },
            {
                "id": "road_passable", "type": "boolean", "required": False,
                "label": {"en": "Is the nearest road passable?",
                          "ar": "هل الطريق الأقرب صالح للمرور؟",
                          "fr": "La route la plus proche est-elle praticable ?",
                          "zh": "最近的道路是否可通行？", "ru": "Проходима ли ближайшая дорога?",
                          "es": "¿Es transitable la carretera más cercana?"},
            },
            {
                "id": "electricity_status", "type": "single_select", "required": True,
                "label": {"en": "What is the current condition of electricity infrastructure in your community following the crisis?"},
                "options": [
                    {"value": "no_damage",  "label": {"en": "No damage observed"}},
                    {"value": "minor",      "label": {"en": "Minor damage (service disruptions but quickly repairable)"}},
                    {"value": "moderate",   "label": {"en": "Moderate damage (partial outages requiring repairs)"}},
                    {"value": "severe",     "label": {"en": "Severe damage (major infrastructure damaged, prolonged outages)"}},
                    {"value": "destroyed",  "label": {"en": "Completely destroyed (no electricity infrastructure functioning)"}},
                    {"value": "unknown",    "label": {"en": "Unknown/cannot be assessed"}},
                ],
            },
            {
                "id": "health_services", "type": "single_select", "required": True,
                "label": {"en": "How would you rate the overall functioning of health services in your community since the event?"},
                "options": [
                    {"value": "fully_functional",    "label": {"en": "Fully functional"}},
                    {"value": "partially_functional","label": {"en": "Partially functional"}},
                    {"value": "largely_disrupted",   "label": {"en": "Largely disrupted"}},
                    {"value": "not_functioning",     "label": {"en": "Not functioning at all"}},
                    {"value": "unknown",             "label": {"en": "Unknown"}},
                ],
            },
            {
                "id": "pressing_needs", "type": "multi_select", "required": True,
                "label": {"en": "What are the most pressing needs?"},
                "options": [
                    {"value": "food_water",        "label": {"en": "Food assistance and safe drinking water"}},
                    {"value": "cash_financial",    "label": {"en": "Cash or financial assistance"}},
                    {"value": "healthcare",        "label": {"en": "Access to healthcare and essential medicines"}},
                    {"value": "shelter",           "label": {"en": "Shelter, housing repair, or temporary accommodation"}},
                    {"value": "livelihoods",       "label": {"en": "Restoration of livelihoods or income sources"}},
                    {"value": "wash",              "label": {"en": "Water, sanitation, and hygiene (toilets, washing facilities)"}},
                    {"value": "basic_services",    "label": {"en": "Restoration of basic services and infrastructure (electricity, roads, schools)"}},
                    {"value": "protection",        "label": {"en": "Protection services and psychosocial support"}},
                    {"value": "community_support", "label": {"en": "Support from local authorities and community organizations"}},
                    {"value": "other",             "label": {"en": "Other, please specify"}},
                ],
            },
        ],
    },
    "earthquake": {
        "crisis_nature": "earthquake",
        "core_fields": ["damage_level", "infrastructure_types", "crisis_nature",
                        "requires_debris_clearing", "photo", "location"],
        "modular_fields": [
            {
                "id": "people_trapped", "type": "boolean", "required": False,
                "label": {"en": "Are people trapped in or near the structure?",
                          "ar": "هل توجد أشخاص محاصرون في البنية أو بالقرب منها؟",
                          "fr": "Des personnes sont-elles piégées dans ou près de la structure ?",
                          "zh": "有人被困在建筑物内或附近吗？",
                          "ru": "Есть ли люди в ловушке внутри или рядом со зданием?",
                          "es": "¿Hay personas atrapadas en o cerca de la estructura?"},
            },
            {
                "id": "aftershock_damage", "type": "boolean", "required": False,
                "label": {"en": "Has aftershock damage been observed?",
                          "ar": "هل لوحظ ضرر من الهزات الارتدادية؟",
                          "fr": "Des dommages dus aux répliques ont-ils été observés ?",
                          "zh": "是否观察到余震造成的损害？",
                          "ru": "Наблюдались ли повреждения от афтершоков?",
                          "es": "¿Se han observado daños por réplicas?"},
            },
            {
                "id": "electricity_status", "type": "single_select", "required": True,
                "label": {"en": "What is the current condition of electricity infrastructure in your community following the crisis?"},
                "options": [
                    {"value": "no_damage",  "label": {"en": "No damage observed"}},
                    {"value": "minor",      "label": {"en": "Minor damage (service disruptions but quickly repairable)"}},
                    {"value": "moderate",   "label": {"en": "Moderate damage (partial outages requiring repairs)"}},
                    {"value": "severe",     "label": {"en": "Severe damage (major infrastructure damaged, prolonged outages)"}},
                    {"value": "destroyed",  "label": {"en": "Completely destroyed (no electricity infrastructure functioning)"}},
                    {"value": "unknown",    "label": {"en": "Unknown/cannot be assessed"}},
                ],
            },
            {
                "id": "health_services", "type": "single_select", "required": True,
                "label": {"en": "How would you rate the overall functioning of health services in your community since the event?"},
                "options": [
                    {"value": "fully_functional",    "label": {"en": "Fully functional"}},
                    {"value": "partially_functional","label": {"en": "Partially functional"}},
                    {"value": "largely_disrupted",   "label": {"en": "Largely disrupted"}},
                    {"value": "not_functioning",     "label": {"en": "Not functioning at all"}},
                    {"value": "unknown",             "label": {"en": "Unknown"}},
                ],
            },
            {
                "id": "pressing_needs", "type": "multi_select", "required": True,
                "label": {"en": "What are the most pressing needs?"},
                "options": [
                    {"value": "food_water",        "label": {"en": "Food assistance and safe drinking water"}},
                    {"value": "cash_financial",    "label": {"en": "Cash or financial assistance"}},
                    {"value": "healthcare",        "label": {"en": "Access to healthcare and essential medicines"}},
                    {"value": "shelter",           "label": {"en": "Shelter, housing repair, or temporary accommodation"}},
                    {"value": "livelihoods",       "label": {"en": "Restoration of livelihoods or income sources"}},
                    {"value": "wash",              "label": {"en": "Water, sanitation, and hygiene (toilets, washing facilities)"}},
                    {"value": "basic_services",    "label": {"en": "Restoration of basic services and infrastructure (electricity, roads, schools)"}},
                    {"value": "protection",        "label": {"en": "Protection services and psychosocial support"}},
                    {"value": "community_support", "label": {"en": "Support from local authorities and community organizations"}},
                    {"value": "other",             "label": {"en": "Other, please specify"}},
                ],
            },
        ],
    },
    "conflict": {
        "crisis_nature": "conflict",
        "core_fields": ["damage_level", "infrastructure_types", "crisis_nature",
                        "requires_debris_clearing", "photo", "location"],
        "modular_fields": [
            {
                "id": "area_accessible", "type": "boolean", "required": False,
                "label": {"en": "Is the affected area accessible?",
                          "ar": "هل المنطقة المتضررة في متناول الوصول؟",
                          "fr": "La zone touchée est-elle accessible ?",
                          "zh": "受影响地区是否可进入？",
                          "ru": "Доступна ли пострадавшая территория?",
                          "es": "¿Es accesible el área afectada?"},
            },
            {
                "id": "civilian_displacement",
                "type": "single_select", "required": False,
                "label": {"en": "Estimate of civilian displacement",
                          "ar": "تقدير نزوح المدنيين",
                          "fr": "Estimation du déplacement de civils",
                          "zh": "平民流离失所估计",
                          "ru": "Оценка перемещения мирных жителей",
                          "es": "Estimación del desplazamiento civil"},
                "options": [
                    {"value": "none",     "label": {"en": "None observed"}},
                    {"value": "few",      "label": {"en": "A few families"}},
                    {"value": "dozens",   "label": {"en": "Dozens of people"}},
                    {"value": "hundreds", "label": {"en": "Hundreds of people"}},
                ],
            },
            {
                "id": "electricity_status", "type": "single_select", "required": True,
                "label": {"en": "What is the current condition of electricity infrastructure in your community following the crisis?"},
                "options": [
                    {"value": "no_damage",  "label": {"en": "No damage observed"}},
                    {"value": "minor",      "label": {"en": "Minor damage (service disruptions but quickly repairable)"}},
                    {"value": "moderate",   "label": {"en": "Moderate damage (partial outages requiring repairs)"}},
                    {"value": "severe",     "label": {"en": "Severe damage (major infrastructure damaged, prolonged outages)"}},
                    {"value": "destroyed",  "label": {"en": "Completely destroyed (no electricity infrastructure functioning)"}},
                    {"value": "unknown",    "label": {"en": "Unknown/cannot be assessed"}},
                ],
            },
            {
                "id": "health_services", "type": "single_select", "required": True,
                "label": {"en": "How would you rate the overall functioning of health services in your community since the event?"},
                "options": [
                    {"value": "fully_functional",    "label": {"en": "Fully functional"}},
                    {"value": "partially_functional","label": {"en": "Partially functional"}},
                    {"value": "largely_disrupted",   "label": {"en": "Largely disrupted"}},
                    {"value": "not_functioning",     "label": {"en": "Not functioning at all"}},
                    {"value": "unknown",             "label": {"en": "Unknown"}},
                ],
            },
            {
                "id": "pressing_needs", "type": "multi_select", "required": True,
                "label": {"en": "What are the most pressing needs?"},
                "options": [
                    {"value": "food_water",        "label": {"en": "Food assistance and safe drinking water"}},
                    {"value": "cash_financial",    "label": {"en": "Cash or financial assistance"}},
                    {"value": "healthcare",        "label": {"en": "Access to healthcare and essential medicines"}},
                    {"value": "shelter",           "label": {"en": "Shelter, housing repair, or temporary accommodation"}},
                    {"value": "livelihoods",       "label": {"en": "Restoration of livelihoods or income sources"}},
                    {"value": "wash",              "label": {"en": "Water, sanitation, and hygiene (toilets, washing facilities)"}},
                    {"value": "basic_services",    "label": {"en": "Restoration of basic services and infrastructure (electricity, roads, schools)"}},
                    {"value": "protection",        "label": {"en": "Protection services and psychosocial support"}},
                    {"value": "community_support", "label": {"en": "Support from local authorities and community organizations"}},
                    {"value": "other",             "label": {"en": "Other, please specify"}},
                ],
            },
        ],
    },
    "hurricane": {
        "crisis_nature": "hurricane",
        "core_fields": ["damage_level", "infrastructure_types", "crisis_nature",
                        "requires_debris_clearing", "photo", "location"],
        "modular_fields": _UNDP_FIELDS,
    },
    "wildfire": {
        "crisis_nature": "wildfire",
        "core_fields": ["damage_level", "infrastructure_types", "crisis_nature",
                        "requires_debris_clearing", "photo", "location"],
        "modular_fields": _UNDP_FIELDS,
    },
    "generic": {
        "crisis_nature": "other",
        "core_fields": ["damage_level", "infrastructure_types", "crisis_nature",
                        "requires_debris_clearing", "photo", "location"],
        "modular_fields": _UNDP_FIELDS,
    },
}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def create_event(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/v1/admin/crisis-events"""
    if not _check_admin_key(req):
        return _FORBIDDEN

    try:
        body = req.get_json()
    except ValueError:
        return _BAD_REQUEST("Invalid JSON body")

    event_id     = (body.get("id") or "").strip().lower()
    name         = (body.get("name") or "").strip()
    country_code = (body.get("country_code") or "").strip().upper()
    region       = (body.get("region") or "").strip().lower()
    crisis_nature = (body.get("crisis_nature") or "generic").strip().lower()
    schema_type  = (body.get("schema_type") or crisis_nature or "generic").strip().lower()
    map_center   = body.get("map_center")  # optional: [lat, lon]

    # Validate required fields
    if not event_id:
        return _BAD_REQUEST("id is required")
    if not _SLUG_RE.match(event_id):
        return _BAD_REQUEST("id must be lowercase alphanumeric with hyphens (3–50 chars)")
    if not name:
        return _BAD_REQUEST("name is required")
    if not country_code or len(country_code) != 2:
        return _BAD_REQUEST("country_code must be a 2-letter ISO code")

    schema = dict(_SCHEMAS.get(schema_type, _SCHEMAS["generic"]))
    schema["crisis_event_id"] = event_id

    doc = {
        "id": event_id,
        "name": name,
        "country_code": country_code,
        "region": region,
        "crisis_nature": crisis_nature,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "form_schema": schema,
        **({"map_center": map_center} if map_center else {}),
    }

    try:
        _container("crisis_events").upsert_item(doc)
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": "db_error", "detail": str(exc)}),
            status_code=500, mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps(doc), status_code=201, mimetype="application/json",
    )


def update_event(req: func.HttpRequest) -> func.HttpResponse:
    """PATCH /api/v1/admin/crisis-events/{event_id}"""
    if not _check_admin_key(req):
        return _FORBIDDEN

    event_id = req.route_params.get("event_id", "").strip()
    if not event_id:
        return _BAD_REQUEST("event_id is required")

    try:
        body = req.get_json()
    except ValueError:
        return _BAD_REQUEST("Invalid JSON body")

    container = _container("crisis_events")

    # Fetch existing doc
    try:
        doc = container.read_item(event_id, partition_key=event_id)
    except cosmos_exc.CosmosResourceNotFoundError:
        return _NOT_FOUND

    # Apply allowed updates
    allowed_statuses = {"active", "archived", "paused"}
    if "status" in body:
        if body["status"] not in allowed_statuses:
            return _BAD_REQUEST(f"status must be one of: {', '.join(allowed_statuses)}")
        doc["status"] = body["status"]
    if "name" in body and body["name"].strip():
        doc["name"] = body["name"].strip()
    if "map_center" in body:
        doc["map_center"] = body["map_center"]

    doc["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        container.upsert_item(doc)
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": "db_error", "detail": str(exc)}),
            status_code=500, mimetype="application/json",
        )

    return func.HttpResponse(json.dumps(doc), status_code=200, mimetype="application/json")
