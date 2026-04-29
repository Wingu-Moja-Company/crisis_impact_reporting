"""
End-to-end smoke test — runs against local or production environment.

Usage:
    python tests/e2e/smoke_test.py --env local --crisis-id ke-flood-dev
    python tests/e2e/smoke_test.py --env prod  --crisis-id ke-flood-2026-04
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

_failures = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}" + (f" — {detail}" if detail else ""))
        _failures.append(name)


_EXPORT_API_KEY = os.environ.get("EXPORT_API_KEY", "")
_INGEST_API_KEY = os.environ.get("INGEST_API_KEY", _EXPORT_API_KEY)
_ADMIN_API_KEY  = os.environ.get("ADMIN_API_KEY", _EXPORT_API_KEY)


def _api_headers() -> dict:
    return {"X-API-Key": _EXPORT_API_KEY} if _EXPORT_API_KEY else {}


def _ingest_headers() -> dict:
    return {"X-API-Key": _INGEST_API_KEY} if _INGEST_API_KEY else {}


def _admin_headers() -> dict:
    return {"X-Admin-Key": _ADMIN_API_KEY} if _ADMIN_API_KEY else {}


def get(url: str, timeout: int = 10) -> tuple[int, dict | str]:
    req = urllib.request.Request(url, headers=_api_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, str(e)


def delete(url: str, timeout: int = 10) -> int:
    req = urllib.request.Request(url, headers=_admin_headers(), method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def post(url: str, fields: dict, timeout: int = 30) -> tuple[int, dict]:
    boundary = "----SmokeTest"
    body_parts = []
    for key, value in fields.items():
        body_parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n"
        )
    body = "".join(body_parts).encode() + f"--{boundary}--\r\n".encode()

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    headers.update(_ingest_headers())

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def run(api_base: str, crisis_event_id: str) -> None:
    print(f"\nSmoke test — {api_base}  crisis={crisis_event_id}\n")

    # 1. Crisis events endpoint
    print("Crisis events API")
    status, body = get(f"{api_base}/v1/crisis-events")
    check("GET /v1/crisis-events returns 200", status == 200, f"got {status}")
    check("Response is a list", isinstance(body, list), type(body).__name__)

    # 2. Stats endpoint
    print("\nStats API")
    status, body = get(f"{api_base}/v1/crisis-events/{crisis_event_id}/stats")
    check("GET /v1/crisis-events/{id}/stats returns 200", status == 200, f"got {status}")
    check("Response has total_reports", isinstance(body, dict) and "total_reports" in body)

    # 3. GeoJSON export
    print("\nGeoJSON export")
    status, body = get(f"{api_base}/v1/reports?crisis_event_id={crisis_event_id}&format=geojson&limit=10")
    check("GET /v1/reports GeoJSON returns 200", status == 200, f"got {status}")
    check("Response is FeatureCollection", isinstance(body, dict) and body.get("type") == "FeatureCollection")

    # 4. CSV export
    print("\nCSV export")
    status, body = get(f"{api_base}/v1/reports?crisis_event_id={crisis_event_id}&format=csv&limit=5")
    check("GET /v1/reports CSV returns 200", status == 200, f"got {status}")
    check("CSV response is a string", isinstance(body, str), type(body).__name__)

    # 5. CAP feed
    print("\nCAP feed")
    status, body = get(f"{api_base}/v1/feeds/cap/{crisis_event_id}.xml")
    check("GET /feeds/cap/{id}.xml returns 200", status == 200, f"got {status}")
    check("CAP feed contains <alert>", isinstance(body, str) and "<alert" in body)

    # Track report IDs created by this test run so we can delete them afterwards
    _test_report_ids: list[str] = []

    # 6. Submit a test report
    print("\nReport submission")
    status, body = post(f"{api_base}/v1/reports", {
        "damage_level":             "minimal",
        "infrastructure_types":     '["residential"]',
        "crisis_nature":            "flood",
        "requires_debris_clearing": "false",
        "crisis_event_id":          crisis_event_id,
        "channel":                  "pwa",
        "gps_lat":                  "-1.2577",
        "gps_lon":                  "36.8614",
        "modular_fields":           "{}",
    })
    check("POST /v1/reports returns 201", status == 201, f"got {status}")
    check("Response has report_id", isinstance(body, dict) and "report_id" in body)
    if isinstance(body, dict) and "report_id" in body:
        _test_report_ids.append(body["report_id"])

    # 7. Missing crisis_event_id → 400
    print("\nValidation")
    status, _ = get(f"{api_base}/v1/reports?format=geojson")
    check("GET /v1/reports without crisis_event_id returns 400", status == 400, f"got {status}")

    # 8. Schema API — get current schema
    print("\nSchema API")
    status, body = get(f"{api_base}/v1/crisis-events/{crisis_event_id}/schema")
    check("GET /v1/crisis-events/{id}/schema returns 200", status == 200, f"got {status}")
    check(
        "Schema has system_fields",
        isinstance(body, dict) and "system_fields" in body,
        str(body)[:120] if isinstance(body, dict) else str(body),
    )
    check(
        "Schema has custom_fields",
        isinstance(body, dict) and "custom_fields" in body,
    )
    check(
        "Schema has version",
        isinstance(body, dict) and body.get("version") is not None,
    )
    check(
        "system_fields has damage_level",
        isinstance(body, dict) and "damage_level" in body.get("system_fields", {}),
    )
    check(
        "system_fields has infrastructure_type",
        isinstance(body, dict) and "infrastructure_type" in body.get("system_fields", {}),
    )

    # 9. Schema version_only endpoint
    status, body = get(f"{api_base}/v1/crisis-events/{crisis_event_id}/schema?version_only=true")
    check("GET /schema?version_only=true returns 200", status == 200, f"got {status}")
    check(
        "version_only response has version key",
        isinstance(body, dict) and "version" in body,
    )

    # 10. Submit report with schema_version + responses (new format)
    print("\nSchema-aware report submission")
    status, body = post(f"{api_base}/v1/reports", {
        "damage_level":         "partial",
        "infrastructure_types": '["residential"]',
        "crisis_event_id":      crisis_event_id,
        "channel":              "pwa",
        "gps_lat":              "-1.2577",
        "gps_lon":              "36.8614",
        "schema_version":       "1",
        "responses":            '{"crisis_nature":"flood","requires_debris_clearing":false}',
    })
    check("POST /v1/reports with schema_version+responses returns 201", status == 201, f"got {status}")
    check("New-format response has report_id", isinstance(body, dict) and "report_id" in body)
    if isinstance(body, dict) and "report_id" in body:
        _test_report_ids.append(body["report_id"])

    # 11. GeoJSON has schema_version and flattened responses
    print("\nGeoJSON schema integration")
    status, body = get(
        f"{api_base}/v1/reports?crisis_event_id={crisis_event_id}&format=geojson&limit=5"
    )
    check("GET /v1/reports GeoJSON still 200 after schema", status == 200, f"got {status}")
    if isinstance(body, dict) and body.get("features"):
        first = body["features"][0]
        props = first.get("properties", {})
        check(
            "GeoJSON feature has schema_version property",
            "schema_version" in props,
            f"keys: {list(props.keys())[:10]}",
        )
    else:
        check("GeoJSON has at least one feature", False, "No features in collection")

    # 12. Schema for unknown event → 404
    status, _ = get(f"{api_base}/v1/crisis-events/nonexistent-smoke-test-event/schema")
    check("GET schema for unknown event returns 404", status == 404, f"got {status}")

    # Cleanup — delete all test reports created during this run so they don't
    # appear on the live dashboard as real data.
    if _test_report_ids:
        print("\nCleanup")
        for report_id in _test_report_ids:
            s = delete(
                f"{api_base}/v1/admin/reports/{report_id}"
                f"?crisis_event_id={crisis_event_id}"
            )
            check(f"DELETE test report {report_id}", s in (200, 204), f"got {s}")

    # Summary
    print(f"\n{'─' * 50}")
    if _failures:
        print(f"{FAIL} {len(_failures)} check(s) failed: {', '.join(_failures)}")
        sys.exit(1)
    else:
        print(f"{PASS} All checks passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="E2E smoke test")
    parser.add_argument("--env", choices=["local", "prod"], default="local")
    parser.add_argument("--crisis-id", default="ke-flood-dev", dest="crisis_id")
    args = parser.parse_args()

    api_base = os.environ.get("API_BASE_URL") or (
        "http://localhost:7071/api" if args.env == "local"
        else "https://api.crisisplatform.io/api"
    )
    run(api_base, args.crisis_id)


if __name__ == "__main__":
    main()
