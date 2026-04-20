"""
Azure Functions HTTP trigger — POST /api/v1/reports
Accepts multipart/form-data with report fields + optional photo.
"""

import json
import azure.functions as func

from functions.ingest.schema import DamageReportSubmission
from functions.ingest.pipeline import process_report


def main(req: func.HttpRequest) -> func.HttpResponse:
    # Parse multipart form data
    try:
        form = req.form
        photo_bytes = req.files.get("photo", None)
        if photo_bytes:
            photo_bytes = photo_bytes.read()

        submission = DamageReportSubmission(
            damage_level=form["damage_level"],
            infrastructure_types=json.loads(form["infrastructure_types"]),
            crisis_nature=form["crisis_nature"],
            requires_debris_clearing=form["requires_debris_clearing"].lower() == "true",
            crisis_event_id=form["crisis_event_id"],
            channel=form["channel"],
            gps_lat=float(form["gps_lat"]) if form.get("gps_lat") else None,
            gps_lon=float(form["gps_lon"]) if form.get("gps_lon") else None,
            what3words_address=form.get("what3words_address"),
            location_description=form.get("location_description"),
            description=form.get("description"),
            infrastructure_name=form.get("infrastructure_name"),
            other_infra_description=form.get("other_infra_description"),
            modular_fields=json.loads(form["modular_fields"]) if form.get("modular_fields") else None,
        )
    except (KeyError, ValueError) as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=400,
            mimetype="application/json",
        )

    # Raw submitter identifier — hashed inside pipeline, never stored raw
    raw_submitter_id = req.headers.get("X-Submitter-Id", req.headers.get("X-Forwarded-For", "anon"))

    try:
        result = process_report(submission, photo_bytes, raw_submitter_id)
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": "processing_failed", "detail": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps(result),
        status_code=201,
        mimetype="application/json",
    )
