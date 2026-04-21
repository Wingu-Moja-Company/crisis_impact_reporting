"""
Seed the API with realistic sample flood-damage reports across Nairobi.

Usage:
    python scripts/seed_sample_reports.py
    python scripts/seed_sample_reports.py --api-url http://localhost:7071/api --crisis-id ke-flood-dev
"""

import argparse
import json
import urllib.request
import urllib.error

REPORTS = [
    # --- Mathare / Eastlands (severe flooding zone) ---
    {
        "gps_lat": -1.2592, "gps_lon": 36.8627,
        "damage_level": "complete",
        "infrastructure_types": '["residential"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Entire ground floor submerged. Wall collapse on northern side. Residents evacuated.",
        "infrastructure_name": "Mathare North flats block C",
        "channel": "pwa",
    },
    {
        "gps_lat": -1.2561, "gps_lon": 36.8598,
        "damage_level": "complete",
        "infrastructure_types": '["residential","community"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Primary school used as shelter — hall roof caved in from water weight.",
        "infrastructure_name": "Mathare Primary School",
        "channel": "telegram",
    },
    {
        "gps_lat": -1.2610, "gps_lon": 36.8652,
        "damage_level": "partial",
        "infrastructure_types": '["transport"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Bridge over Mathare River has large section washed out. Pedestrian access cut off.",
        "infrastructure_name": "Mathare River footbridge",
        "channel": "telegram",
    },

    # --- Westlands / Parklands ---
    {
        "gps_lat": -1.2617, "gps_lon": 36.8016,
        "damage_level": "minimal",
        "infrastructure_types": '["commercial"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "false",
        "description": "Basement parking flooded. Ground floor retail shops have mud deposits up to 10 cm.",
        "infrastructure_name": "Westgate Shopping Mall annex",
        "channel": "pwa",
    },
    {
        "gps_lat": -1.2551, "gps_lon": 36.8088,
        "damage_level": "partial",
        "infrastructure_types": '["utility"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "false",
        "description": "Transformer substation flooded. Power outage affecting ~2,000 households.",
        "infrastructure_name": "KPLC Parklands substation",
        "channel": "pwa",
    },

    # --- CBD / River Road area ---
    {
        "gps_lat": -1.2833, "gps_lon": 36.8172,
        "damage_level": "partial",
        "infrastructure_types": '["government"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Ground floor offices flooded. Archives and records partially destroyed.",
        "infrastructure_name": "Nairobi City Hall annex",
        "channel": "pwa",
    },
    {
        "gps_lat": -1.2864, "gps_lon": 36.8219,
        "damage_level": "minimal",
        "infrastructure_types": '["transport"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Road surface cracked and potholed after flash flood. Slow-moving traffic.",
        "infrastructure_name": "River Road / Ronald Ngala St junction",
        "channel": "telegram",
    },

    # --- Kibera ---
    {
        "gps_lat": -1.3126, "gps_lon": 36.7869,
        "damage_level": "complete",
        "infrastructure_types": '["residential"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Row of 12 single-room units swept away by Ngong River overflow. Families displaced.",
        "infrastructure_name": "Kibera Soweto East row housing",
        "channel": "telegram",
    },
    {
        "gps_lat": -1.3152, "gps_lon": 36.7908,
        "damage_level": "complete",
        "infrastructure_types": '["community","utility"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Health clinic flooded. Medical supplies destroyed. Water pump non-operational.",
        "infrastructure_name": "Kibera Health Clinic Block B",
        "channel": "telegram",
    },
    {
        "gps_lat": -1.3102, "gps_lon": 36.7832,
        "damage_level": "partial",
        "infrastructure_types": '["transport"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Main access road into Kibera Village blocked by large debris pile.",
        "infrastructure_name": "Olympic Estate access road",
        "channel": "telegram",
    },

    # --- Karen / Lang'ata ---
    {
        "gps_lat": -1.3445, "gps_lon": 36.7128,
        "damage_level": "minimal",
        "infrastructure_types": '["residential"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "false",
        "description": "Perimeter wall collapsed. Garden flooded but main structure intact.",
        "infrastructure_name": "Private residence, Karen Hardy",
        "channel": "pwa",
    },
    {
        "gps_lat": -1.3381, "gps_lon": 36.7312,
        "damage_level": "partial",
        "infrastructure_types": '["public_space"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Football pitch and children's play area completely waterlogged. Equipment damaged.",
        "infrastructure_name": "Lang'ata Community Park",
        "channel": "pwa",
    },

    # --- Kasarani / Thika Road ---
    {
        "gps_lat": -1.2218, "gps_lon": 36.8952,
        "damage_level": "partial",
        "infrastructure_types": '["commercial","transport"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Service road running parallel to Thika Superhighway submerged. 3 matatus stranded.",
        "infrastructure_name": "Kasarani service road near Seasons",
        "channel": "pwa",
    },
    {
        "gps_lat": -1.2195, "gps_lon": 36.8910,
        "damage_level": "minimal",
        "infrastructure_types": '["utility"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "false",
        "description": "Nairobi Water pumping station — minor ingress into control room. Operational.",
        "infrastructure_name": "Kasarani pumping station",
        "channel": "telegram",
    },

    # --- Ruiru / outskirts (slightly north) ---
    {
        "gps_lat": -1.1465, "gps_lon": 36.9606,
        "damage_level": "complete",
        "infrastructure_types": '["transport"]',
        "crisis_nature": "flood",
        "requires_debris_clearing": "true",
        "description": "Bridge over Ruiru River washed away. Road to Thika completely cut.",
        "infrastructure_name": "Ruiru River bridge, Kamakis road",
        "channel": "telegram",
    },
]


def post_report(api_base: str, crisis_id: str, report: dict) -> tuple[int, str]:
    boundary = "----SeedData"
    fields = {**report, "crisis_event_id": crisis_id, "modular_fields": "{}"}
    body_parts = []
    for key, value in fields.items():
        body_parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'
        )
    body = "".join(body_parts).encode() + f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{api_base}/v1/reports",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return resp.status, data.get("report_id", "?")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:120]
    except Exception as exc:
        return 0, str(exc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="https://func-crisis-pipeline-ob7ravt3zfbzi.azurewebsites.net/api")
    parser.add_argument("--crisis-id", default="ke-flood-dev")
    args = parser.parse_args()

    print(f"Seeding {len(REPORTS)} sample reports → {args.api_url}  crisis={args.crisis_id}\n")
    ok = 0
    for r in REPORTS:
        status, result = post_report(args.api_url, args.crisis_id, r)
        icon = "✓" if status == 201 else "✗"
        label = r.get("infrastructure_name") or r["description"][:60]
        print(f"  {icon} [{status}] {label[:60]}")
        if status == 201:
            ok += 1
    print(f"\n{ok}/{len(REPORTS)} reports seeded successfully.")


if __name__ == "__main__":
    main()
