"""
Load simulation — submits N synthetic reports against the ingestion API.
Used for local load testing and CI performance benchmarks.

Usage:
    python tests/load/simulate_reports.py --count 1000 --crisis-id ke-flood-dev
    python tests/load/simulate_reports.py --count 500  --crisis-id ke-flood-dev --concurrency 20
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:7071/api")

DAMAGE_LEVELS    = ["minimal", "partial", "complete"]
INFRA_TYPES      = ["residential", "commercial", "transport", "community"]
CRISIS_NATURES   = ["flood", "earthquake", "conflict"]
CHANNELS         = ["pwa", "telegram"]

# Nairobi bounding box
LAT_MIN, LAT_MAX = -1.35, -1.15
LON_MIN, LON_MAX =  36.70,  37.00


def _random_report(crisis_event_id: str) -> dict:
    return {
        "damage_level":             random.choice(DAMAGE_LEVELS),
        "infrastructure_types":     json.dumps([random.choice(INFRA_TYPES)]),
        "crisis_nature":            random.choice(CRISIS_NATURES),
        "requires_debris_clearing": str(random.choice([True, False])).lower(),
        "crisis_event_id":          crisis_event_id,
        "channel":                  random.choice(CHANNELS),
        "gps_lat":                  str(round(random.uniform(LAT_MIN, LAT_MAX), 6)),
        "gps_lon":                  str(round(random.uniform(LON_MIN, LON_MAX), 6)),
        "description":              "Simulated load-test report",
    }


def _submit(fields: dict) -> tuple[int, float]:
    boundary = "----LoadTest"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
        for k, v in fields.items()
    ]
    body = "".join(parts).encode() + f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{API_BASE}/v1/reports",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, time.monotonic() - start
    except urllib.error.HTTPError as e:
        return e.code, time.monotonic() - start
    except Exception:
        return 0, time.monotonic() - start


def run(count: int, crisis_event_id: str, concurrency: int) -> None:
    print(f"Submitting {count} reports to {API_BASE} (concurrency={concurrency}) …\n")
    reports = [_random_report(crisis_event_id) for _ in range(count)]

    successes, failures = 0, 0
    latencies: list[float] = []
    started = time.monotonic()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_submit, r): r for r in reports}
        for i, future in enumerate(as_completed(futures), 1):
            status, latency = future.result()
            latencies.append(latency)
            if status == 201:
                successes += 1
            else:
                failures += 1
            if i % 100 == 0 or i == count:
                print(f"  {i}/{count} — {successes} ok, {failures} failed", end="\r")

    elapsed = time.monotonic() - started
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]

    print(f"\n\nResults:")
    print(f"  Total:      {count}")
    print(f"  Successes:  {successes}")
    print(f"  Failures:   {failures}")
    print(f"  Elapsed:    {elapsed:.1f}s  ({count / elapsed:.1f} req/s)")
    print(f"  Latency p50: {p50 * 1000:.0f} ms")
    print(f"  Latency p95: {p95 * 1000:.0f} ms")

    if failures > count * 0.01:
        print("\nERROR: failure rate exceeded 1%")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test report submission")
    parser.add_argument("--count",       type=int, default=1000)
    parser.add_argument("--crisis-id",   default="ke-flood-dev", dest="crisis_id")
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    run(args.count, args.crisis_id, args.concurrency)


if __name__ == "__main__":
    main()
