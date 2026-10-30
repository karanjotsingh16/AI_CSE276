from __future__ import annotations

from pathlib import Path
import json

from route_engine import (
    DEFAULT_PROCESSED_GRAPH_PATH,
    GraphFileNotFoundError,
    InvalidCoordinateError,
    OutOfCoverageError,
    RouteEngine,
    UnreachableDestinationError,
)

# Locations matching frontend/src/data/locations.ts
SHILLONG = {"name": "Shillong (HQ Logistics Hub)", "lat": 25.5788, "lng": 91.8933}
SOHRA = {"name": "Sohra / Cherrapunji (Southern Hills)", "lat": 25.2750, "lng": 91.7323}
MAIRANG = {"name": "Mairang (West Khasi Hills Transit)", "lat": 25.5653, "lng": 91.6375}
GUWAHATI = {"name": "Guwahati (Regional Depot)", "lat": 26.1445, "lng": 91.7362}
JOWAI = {"name": "Jowai (Jaintia Hills Sub-Depot)", "lat": 25.4475, "lng": 92.2030}


def assert_valid_route_payload(route: dict, expected_type: str) -> None:
    assert route["route_type"] == expected_type, f"Expected {expected_type}, got {route['route_type']}"
    assert isinstance(route["node_ids"], list) and len(route["node_ids"]) >= 2
    assert route["num_nodes"] == len(route["node_ids"])
    assert isinstance(route["distance_km"], float) and route["distance_km"] > 0
    assert isinstance(route["estimated_duration_min"], float) and route["estimated_duration_min"] > 0
    assert route["duration_is_estimate"] is True
    assert "not a live traffic prediction" in route["duration_estimate_note"]

    geom = route["geometry"]
    assert geom["type"] == "LineString"
    coords = geom["coordinates"]
    assert isinstance(coords, list) and len(coords) >= route["num_nodes"]
    # Verify GeoJSON [longitude, latitude] order for Meghalaya (~91-92 E, ~25-26 N)
    first_lng, first_lat = coords[0]
    assert 91.0 <= first_lng <= 93.0, f"Expected longitude first in GeoJSON, got {coords[0]}"
    assert 25.0 <= first_lat <= 26.0, f"Expected latitude second in GeoJSON, got {coords[0]}"


def main() -> None:
    print("=" * 72)
    print("TESTING STANDALONE ROUTE ENGINE (SIH 26002 — NER SmartRoute)")
    print("=" * 72)

    print(f"\n[1] Initializing RouteEngine with: {DEFAULT_PROCESSED_GRAPH_PATH}")
    engine = RouteEngine()
    assert engine.load_count == 1, f"Expected load_count == 1, got {engine.load_count}"
    print(
        f"    Loaded graph once: {engine.graph.number_of_nodes()} nodes, "
        f"{engine.graph.number_of_edges()} directed edges (load_count={engine.load_count})."
    )

    print("\n[2] Testing valid route: Shillong -> Sohra")
    result = engine.calculate_routes(
        origin_lat=SHILLONG["lat"],
        origin_lng=SHILLONG["lng"],
        destination_lat=SOHRA["lat"],
        destination_lng=SOHRA["lng"],
    )
    shortest = result["routes"]["shortest"]
    fastest = result["routes"]["estimated_fastest"]

    assert_valid_route_payload(shortest, "shortest")
    assert_valid_route_payload(fastest, "estimated_fastest")
    assert shortest["distance_km"] <= fastest["distance_km"], (
        "Shortest route distance should be <= fastest route distance"
    )
    assert fastest["estimated_duration_min"] <= shortest["estimated_duration_min"], (
        "Estimated fastest route duration should be <= shortest route duration"
    )
    assert engine.load_count == 1, "Graph should not be reloaded on route calculation"

    summary = {
        "origin_snap": result["origin"],
        "destination_snap": result["destination"],
        "travel_time_disclaimer": result["travel_time_disclaimer"],
        "shortest_route": {
            "num_nodes": shortest["num_nodes"],
            "first_3_nodes": shortest["node_ids"][:3],
            "last_3_nodes": shortest["node_ids"][-3:],
            "distance_km": shortest["distance_km"],
            "estimated_duration_min": shortest["estimated_duration_min"],
            "geojson_type": shortest["geometry"]["type"],
            "num_geometry_points": len(shortest["geometry"]["coordinates"]),
            "sample_start_coord_lng_lat": shortest["geometry"]["coordinates"][0],
            "sample_end_coord_lng_lat": shortest["geometry"]["coordinates"][-1],
        },
        "estimated_fastest_route": {
            "num_nodes": fastest["num_nodes"],
            "first_3_nodes": fastest["node_ids"][:3],
            "last_3_nodes": fastest["node_ids"][-3:],
            "distance_km": fastest["distance_km"],
            "estimated_duration_min": fastest["estimated_duration_min"],
            "geojson_type": fastest["geometry"]["type"],
            "num_geometry_points": len(fastest["geometry"]["coordinates"]),
            "sample_start_coord_lng_lat": fastest["geometry"]["coordinates"][0],
            "sample_end_coord_lng_lat": fastest["geometry"]["coordinates"][-1],
        },
    }
    print(json.dumps(summary, indent=2))

    print("\n[3] Testing second valid route (Shillong -> Mairang) to verify single graph load")
    mairang_res = engine.calculate_routes(
        origin_lat=SHILLONG["lat"],
        origin_lng=SHILLONG["lng"],
        destination_lat=MAIRANG["lat"],
        destination_lng=MAIRANG["lng"],
    )
    assert_valid_route_payload(mairang_res["routes"]["shortest"], "shortest")
    assert_valid_route_payload(mairang_res["routes"]["estimated_fastest"], "estimated_fastest")
    assert engine.load_count == 1, f"Expected load_count == 1 after second query, got {engine.load_count}"
    print(
        f"    Shillong -> Mairang shortest: {mairang_res['routes']['shortest']['distance_km']} km "
        f"({mairang_res['routes']['shortest']['estimated_duration_min']} min est.) | "
        f"fastest: {mairang_res['routes']['estimated_fastest']['distance_km']} km "
        f"({mairang_res['routes']['estimated_fastest']['estimated_duration_min']} min est.) | "
        f"engine.load_count={engine.load_count}"
    )

    print("\n[4] Testing out-of-coverage locations (Guwahati & Jowai > 3,000 m limit)")
    for loc in (GUWAHATI, JOWAI):
        try:
            engine.calculate_routes(
                origin_lat=SHILLONG["lat"],
                origin_lng=SHILLONG["lng"],
                destination_lat=loc["lat"],
                destination_lng=loc["lng"],
            )
            raise AssertionError(f"Expected OutOfCoverageError for {loc['name']}, but succeeded!")
        except OutOfCoverageError as err:
            print(f"    Correctly rejected {loc['name']}: {err}")

    print("\n[5] Testing invalid coordinates")
    invalid_cases = [
        (105.0, 91.8933, 25.2750, 91.7323, "latitude > 90"),
        (25.5788, 210.0, 25.2750, 91.7323, "longitude > 180"),
        (float("nan"), 91.8933, 25.2750, 91.7323, "NaN latitude"),
        ("25.5788", 91.8933, 25.2750, 91.7323, "string latitude"),
        (True, 91.8933, 25.2750, 91.7323, "boolean latitude"),
    ]
    for o_lat, o_lng, d_lat, d_lng, desc in invalid_cases:
        try:
            engine.calculate_routes(o_lat, o_lng, d_lat, d_lng)
            raise AssertionError(f"Expected InvalidCoordinateError for case {desc!r}")
        except InvalidCoordinateError as err:
            print(f"    Correctly rejected ({desc}): {err}")

    print("\n[6] Testing missing GraphML file handling")
    missing_path = Path(__file__).resolve().parent / "data" / "processed" / "nonexistent_graph.graphml"
    try:
        RouteEngine(graph_path=missing_path)
        raise AssertionError("Expected GraphFileNotFoundError for missing file")
    except GraphFileNotFoundError as err:
        print(f"    Correctly rejected missing file: {err}")

    print("\n[7] Testing unreachable destination handling")
    isolated_node_id = -999999
    engine.graph.add_node(isolated_node_id, y=25.40, x=91.80)
    try:
        engine._compute_single_route(
            origin_node=result["origin"]["node_id"],
            destination_node=isolated_node_id,
            weight_attr="length",
            route_type="shortest",
        )
        raise AssertionError("Expected UnreachableDestinationError for isolated node")
    except UnreachableDestinationError as err:
        print(f"    Correctly rejected unreachable destination: {err}")
    finally:
        engine.graph.remove_node(isolated_node_id)

    print("\n" + "=" * 72)
    print("ALL ROUTE ENGINE TESTS PASSED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()

