"""
NER SmartRoute — Unified Master Test Suite Runner (SIH 26002)

Executes all 9 unit and integration test suites covering Modules A through H:
  1. test_alerts_system.py (Module G - Alerts & Deduplication)
  2. test_vehicle_tracking.py (Module F - GPS Fleet & Deliveries)
  3. test_accessibility_and_reports.py (Module D & E - Road Accessibility & Field Reports)
  4. test_weather_and_disruptions.py (Module C - Open-Meteo & Spatial Disruptions)
  5. test_route_scoring.py (Module A - Multi-Criteria Explainable Route Scoring)
  6. test_route_engine.py (Module A - OSMnx NetworkX Graph Routing)
  7. test_route_ranking_ml.py (Module B - Pairwise Route-Ranking ML)
  8. test_geocoding_and_regions.py (Module A - 8-State NER Catalog & Gazetteer)
  9. test_demand_clustering.py (K-Means Projected Clustering)
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

TEST_SUITES = [
    ("test_alerts_system.py", "Module G: Multi-Hazard Alerts & Deduplication"),
    ("test_vehicle_tracking.py", "Module F: GPS Vehicle & Delivery Tracking"),
    ("test_accessibility_and_reports.py", "Module D & E: Road Accessibility & Field Reporting"),
    ("test_weather_and_disruptions.py", "Module C: Live Weather & Spatial Disruptions"),
    ("test_route_scoring.py", "Module A: Multi-Criteria Explainable Route Scoring"),
    ("test_route_engine.py", "Module A: Graph-Based Routing & Alternative Corridors"),
    ("test_route_ranking_ml.py", "Module B: Pairwise Route-Ranking ML Pipeline"),
    ("test_geocoding_and_regions.py", "Module A: Multi-Region Catalog & Gazetteer"),
    ("test_demand_clustering.py", "Demonstration: K-Means Projected Demand Clustering"),
]


def run_suite(filename: str, description: str) -> tuple[bool, float, str]:
    suite_path = BASE_DIR / filename
    if not suite_path.exists():
        return False, 0.0, f"File not found: {filename}"

    start_t = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(suite_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=180,
        )
        duration = time.time() - start_t
        passed = (proc.returncode == 0)
        output = proc.stdout + proc.stderr
        return passed, duration, output
    except Exception as exc:
        duration = time.time() - start_t
        return False, duration, f"Exception during execution: {exc}"


def main() -> int:
    print("=" * 80, flush=True)
    print("NER SMARTROUTE — FULL REGRESSION TEST RUNNER (SIH 26002)", flush=True)
    print("Academic Track: CSE276 | Pilot Region: Meghalaya & North-East India", flush=True)
    print("=" * 80, flush=True)

    results: list[tuple[str, str, bool, float]] = []
    overall_start = time.time()

    for idx, (filename, desc) in enumerate(TEST_SUITES, 1):
        print(f"\n[{idx}/{len(TEST_SUITES)}] Running {filename}...", flush=True)
        print(f"      Scope: {desc}", flush=True)
        passed, duration, out = run_suite(filename, desc)
        status_label = "PASSED" if passed else "FAILED"
        print(f"      Result: {status_label} ({duration:.2f}s)", flush=True)
        if not passed:
            print("--- OUTPUT SNIPPET ---")
            lines = out.strip().splitlines()
            for line in lines[-20:]:
                print(f"  > {line}")
            print("----------------------")
        results.append((filename, desc, passed, duration))

    overall_duration = time.time() - overall_start

    print("\n" + "=" * 80)
    print("FINAL TEST SUMMARY")
    print("=" * 80)
    print(f"{'Test File':<36} {'Duration':<10} {'Status'}")
    print("-" * 80)

    all_passed = True
    for fname, _, passed, dur in results:
        status_str = "[ PASS ]" if passed else "[ FAIL ]"
        print(f"{fname:<36} {dur:>7.2f}s   {status_str}")
        if not passed:
            all_passed = False

    print("-" * 80)
    print(f"Total Suites: {len(results)} | Duration: {overall_duration:.2f}s")
    if all_passed:
        print("RESULT: ALL 9 TEST SUITES PASSED CLEANLY (100% REGRESSION PASS)")
        print("=" * 80)
        return 0
    else:
        print("RESULT: ONE OR MORE SUITES FAILED")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
