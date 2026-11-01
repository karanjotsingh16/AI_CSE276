from __future__ import annotations

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
for _p in [_ROOT, _ROOT / 'core', _ROOT / 'services']:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


import json
from typing import Any

from fastapi.testclient import TestClient

from main import VITE_DEV_ORIGIN, app, get_route_engine
from route_engine import GraphFileNotFoundError, UnreachableDestinationError

SHILLONG = {"lat": 25.5788, "lng": 91.8933}
SOHRA = {"lat": 25.2750, "lng": 91.7323}
MAIRANG = {"lat": 25.5653, "lng": 91.6375}
GUWAHATI = {"lat": 26.1445, "lng": 91.7362}
JOWAI = {"lat": 25.4475, "lng": 92.2030}


def main() -> None:
    print("=" * 72)
    print("TESTING FASTAPI LAYER (SIH 26002 — NER SmartRoute)")
    print("=" * 72)

    with TestClient(app) as client:
        # 1. Test GET /health
        print("\n[1] Testing GET /health")
        health_res = client.get("/health")
        assert health_res.status_code == 200, f"Expected 200, got {health_res.status_code}"
        health_data = health_res.json()
        assert health_data["status"] == "ok"
        assert health_data["graph_loaded"] is True
        assert health_data["nodes"] == 21764
        assert health_data["directed_edges"] == 53888
        assert health_data["max_snap_distance_m"] == 3000.0
        assert health_data["load_count"] == 1
        print(json.dumps(health_data, indent=2))

        # 2. Test POST /api/routes (Shillong -> Sohra, nested format, real graph)
        print("\n[2] Testing POST /api/routes (Shillong -> Sohra, nested payload)")
        route_res = client.post(
            "/api/routes",
            json={
                "origin": SHILLONG,
                "destination": SOHRA,
            },
        )
        assert route_res.status_code == 200, f"Expected 200, got {route_res.status_code}: {route_res.text}"
        route_data = route_res.json()

        assert route_data["origin"]["node_id"] == 3428125750
        assert route_data["destination"]["node_id"] == 9667317115
        assert route_data["max_snap_distance_m"] == 3000.0
        assert "not real-time traffic predictions" in route_data["travel_time_disclaimer"]

        shortest = route_data["routes"]["shortest"]
        fastest = route_data["routes"]["estimated_fastest"]

        assert shortest["num_nodes"] == 301
        assert shortest["distance_km"] == 50.53
        assert shortest["estimated_duration_min"] == 105.1
        assert shortest["geometry"]["type"] == "LineString"
        assert len(shortest["geometry"]["coordinates"]) == 2908

        assert fastest["num_nodes"] == 218
        assert fastest["distance_km"] == 52.88
        assert fastest["estimated_duration_min"] == 82.7
        assert fastest["geometry"]["type"] == "LineString"
        assert len(fastest["geometry"]["coordinates"]) == 2757

        route_preview = {
            "origin": route_data["origin"],
            "destination": route_data["destination"],
            "max_snap_distance_m": route_data["max_snap_distance_m"],
            "travel_time_disclaimer": route_data["travel_time_disclaimer"],
            "routes": {
                "shortest": {
                    k: (v if k != "geometry" and k != "node_ids" else f"<{len(v) if isinstance(v, list) else len(v['coordinates'])} items>")
                    for k, v in shortest.items()
                },
                "estimated_fastest": {
                    k: (v if k != "geometry" and k != "node_ids" else f"<{len(v) if isinstance(v, list) else len(v['coordinates'])} items>")
                    for k, v in fastest.items()
                },
            },
        }
        print(json.dumps(route_preview, indent=2))

        # 3. Test POST /api/routes with flat payload format & verify single graph load
        print("\n[3] Testing POST /api/routes (Shillong -> Mairang, flat payload) & single graph load")
        flat_res = client.post(
            "/api/routes",
            json={
                "origin_lat": SHILLONG["lat"],
                "origin_lng": SHILLONG["lng"],
                "destination_lat": MAIRANG["lat"],
                "destination_lng": MAIRANG["lng"],
            },
        )
        assert flat_res.status_code == 200
        health_after = client.get("/health").json()
        assert health_after["load_count"] == 1, f"Graph reloaded! load_count={health_after['load_count']}"
        print(
            f"    Status 200 OK | shortest={flat_res.json()['routes']['shortest']['distance_km']} km | "
            f"fastest={flat_res.json()['routes']['estimated_fastest']['distance_km']} km | "
            f"load_count={health_after['load_count']}"
        )

        # 4. Test out-of-coverage rejection (Guwahati & Jowai on real graph)
        print("\n[4] Testing out-of-coverage rejection (Guwahati & Jowai > 3,000 m)")
        for name, coords in (("Guwahati", GUWAHATI), ("Jowai", JOWAI)):
            ooc_res = client.post(
                "/api/routes",
                json={"origin": SHILLONG, "destination": coords},
            )
            assert ooc_res.status_code == 422, f"Expected 422 for {name}, got {ooc_res.status_code}"
            err_body = ooc_res.json()
            assert err_body["error"] == "out_of_coverage"
            assert "exceeds the 3000 m maximum snapping distance" in err_body["detail"]
            assert "Traceback" not in ooc_res.text
            print(f"    {name} -> HTTP {ooc_res.status_code}: {json.dumps(err_body)}")

        # 5. Test invalid coordinates rejection
        print("\n[5] Testing invalid coordinates rejection")
        invalid_payloads: list[tuple[str, dict[str, Any]]] = [
            ("latitude > 90", {"origin": {"lat": 105.0, "lng": 91.8933}, "destination": SOHRA}),
            ("longitude < -180", {"origin": SHILLONG, "destination": {"lat": 25.275, "lng": -195.0}}),
            ("missing destination", {"origin": SHILLONG}),
            ("string coordinate", {"origin": {"lat": "not-a-number", "lng": 91.8933}, "destination": SOHRA}),
            ("boolean coordinate", {"origin": {"lat": True, "lng": 91.8933}, "destination": SOHRA}),
        ]
        for label, bad_payload in invalid_payloads:
            bad_res = client.post("/api/routes", json=bad_payload)
            assert bad_res.status_code == 422, f"Expected 422 for {label}, got {bad_res.status_code}"
            bad_body = bad_res.json()
            assert bad_body["error"] == "invalid_coordinates"
            assert "Traceback" not in bad_res.text
            print(f"    {label} -> HTTP {bad_res.status_code}: {json.dumps(bad_body)}")

        # 6. Test CORS configuration for http://localhost:5173
        print("\n[6] Testing CORS headers for Vite origin (http://localhost:5173)")
        cors_ok = client.options(
            "/api/routes",
            headers={
                "Origin": VITE_DEV_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )
        assert cors_ok.status_code == 200
        assert cors_ok.headers.get("access-control-allow-origin") == VITE_DEV_ORIGIN
        print(
            f"    Allowed origin {VITE_DEV_ORIGIN} -> "
            f"access-control-allow-origin: {cors_ok.headers.get('access-control-allow-origin')}"
        )

        cors_blocked = client.options(
            "/api/routes",
            headers={
                "Origin": "http://unauthorized.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert cors_blocked.headers.get("access-control-allow-origin") is None
        print("    Unauthorized origin http://unauthorized.example.com -> CORS header omitted as expected")

        # 7. Test isolated error-handling mapping (404 Unreachable & 503 Graph Unavailable) using mock override
        print("\n[7] Testing isolated exception mapping via dependency override")

        class MockUnreachableEngine:
            def calculate_routes(self, **_kwargs: Any) -> dict[str, Any]:
                raise UnreachableDestinationError(
                    "No directed road path exists from origin node 100 to destination node 200."
                )

        app.dependency_overrides[get_route_engine] = lambda: MockUnreachableEngine()
        try:
            unreach_res = client.post(
                "/api/routes",
                json={"origin": SHILLONG, "destination": SOHRA},
            )
            assert unreach_res.status_code == 404
            assert unreach_res.json()["error"] == "unreachable_destination"
            print(f"    UnreachableDestinationError -> HTTP {unreach_res.status_code}: {json.dumps(unreach_res.json())}")
        finally:
            app.dependency_overrides.clear()

        def raise_missing_graph() -> Any:
            raise GraphFileNotFoundError("Processed road graph file not found.")

        app.dependency_overrides[get_route_engine] = raise_missing_graph
        try:
            unavail_res = client.post(
                "/api/routes",
                json={"origin": SHILLONG, "destination": SOHRA},
            )
            assert unavail_res.status_code == 503
            assert unavail_res.json()["error"] == "graph_unavailable"
            print(f"    GraphFileNotFoundError -> HTTP {unavail_res.status_code}: {json.dumps(unavail_res.json())}")
        finally:
            app.dependency_overrides.clear()

    print("\n" + "=" * 72)
    print("ALL FASTAPI TESTS PASSED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()

