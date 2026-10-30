from pathlib import Path
import json

import networkx as nx
import numpy as np
import osmnx as ox

BASE_DIR = Path(__file__).resolve().parent
RAW_GRAPH_PATH = BASE_DIR / "data" / "raw" / "shillong_roads.graphml"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_GRAPH_PATH = PROCESSED_DIR / "shillong_roads_clean.graphml"
REPORT_DIR = BASE_DIR / "reports"
AUDIT_REPORT_PATH = REPORT_DIR / "road_data_audit.json"

# Realistic mountain driving speeds (km/h) for the Shillong-Sohra corridor (Meghalaya)
MOUNTAIN_HIGHWAY_SPEEDS_KPH = {
    "trunk": 45.0,
    "trunk_link": 35.0,
    "primary": 40.0,
    "primary_link": 30.0,
    "secondary": 35.0,
    "secondary_link": 25.0,
    "tertiary": 28.0,
    "tertiary_link": 22.0,
    "unclassified": 22.0,
    "residential": 20.0,
    "living_street": 15.0,
}
FALLBACK_SPEED_KPH = 25.0

# Maximum allowed snapping distance (metres) before a coordinate is flagged as outside graph coverage
MAX_SNAP_DISTANCE_M = 3000.0

KNOWN_LOCATIONS = [
    {"id": "shillong", "name": "Shillong (HQ Logistics Hub)", "lat": 25.5788, "lng": 91.8933},
    {"id": "sohra", "name": "Sohra / Cherrapunji (Southern Hills)", "lat": 25.2750, "lng": 91.7323},
    {"id": "mairang", "name": "Mairang (West Khasi Hills Transit)", "lat": 25.5653, "lng": 91.6375},
    {"id": "dawki", "name": "Dawki (Border River Outpost)", "lat": 25.1911, "lng": 92.0232},
    {"id": "jowai", "name": "Jowai (Jaintia Hills Sub-Depot)", "lat": 25.4475, "lng": 92.2030},
    {"id": "nongpoh", "name": "Nongpoh (NH-6 Transit Hub)", "lat": 25.9037, "lng": 91.8803},
    {"id": "guwahati", "name": "Guwahati (Regional Depot)", "lat": 26.1445, "lng": 91.7362},
]


def snap_coordinate_to_node(
    G: nx.MultiDiGraph,
    lat: float,
    lng: float,
    max_snap_distance_m: float = MAX_SNAP_DISTANCE_M,
) -> dict:
    """Snap a (lat, lng) coordinate to the nearest graph node and validate snap distance."""
    node_id, dist_m = ox.distance.nearest_nodes(G, X=lng, Y=lat, return_dist=True)
    node_data = G.nodes[node_id]
    within_coverage = float(dist_m) <= max_snap_distance_m
    return {
        "node_id": int(node_id),
        "node_lat": round(float(node_data["y"]), 6),
        "node_lng": round(float(node_data["x"]), 6),
        "snap_distance_m": round(float(dist_m), 2),
        "within_coverage": bool(within_coverage),
    }


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading raw graph from: {RAW_GRAPH_PATH}")
    G_raw = ox.load_graphml(RAW_GRAPH_PATH)
    raw_nodes = G_raw.number_of_nodes()
    raw_edges = G_raw.number_of_edges()
    raw_wcc = nx.number_weakly_connected_components(G_raw)
    raw_scc = nx.number_strongly_connected_components(G_raw)

    print(
        f"Raw graph: {raw_nodes} nodes, {raw_edges} edges, "
        f"{raw_wcc} weakly connected components, {raw_scc} strongly connected components."
    )

    # 1. Retain only the largest strongly connected component so every node is mutually reachable
    G = ox.truncate.largest_component(G_raw, strongly=True)

    # 2. Impute missing speeds (km/h) and travel times (seconds) for mountain road classes
    G = ox.routing.add_edge_speeds(
        G,
        hwy_speeds=MOUNTAIN_HIGHWAY_SPEEDS_KPH,
        fallback=FALLBACK_SPEED_KPH,
    )
    G = ox.routing.add_edge_travel_times(G)

    # 3. Save cleaned graph to processed directory and update raw graph so all loaders get clean data
    ox.save_graphml(G, filepath=PROCESSED_GRAPH_PATH)
    ox.save_graphml(G, filepath=RAW_GRAPH_PATH)

    nodes, edges = ox.graph_to_gdfs(G)

    # 4. Verify snapping and coverage for all frontend locations
    location_checks = {}
    for loc in KNOWN_LOCATIONS:
        snap = snap_coordinate_to_node(G, loc["lat"], loc["lng"])
        location_checks[loc["id"]] = {
            "name": loc["name"],
            "query_lat": loc["lat"],
            "query_lng": loc["lng"],
            **snap,
        }

    # 5. Verify a test route between Shillong and Sohra using both length and travel_time weights
    shillong_node = location_checks["shillong"]["node_id"]
    sohra_node = location_checks["sohra"]["node_id"]
    shortest_by_len = nx.shortest_path(G, shillong_node, sohra_node, weight="length")
    fastest_by_time = nx.shortest_path(G, shillong_node, sohra_node, weight="travel_time")

    len_dist_km = round(
        nx.path_weight(G, shortest_by_len, weight="length") / 1000.0, 2
    )
    time_dist_km = round(
        nx.path_weight(G, fastest_by_time, weight="length") / 1000.0, 2
    )
    fastest_duration_min = round(
        nx.path_weight(G, fastest_by_time, weight="travel_time") / 60.0, 1
    )

    report = {
        "region": "Shillong–Sohra region, Meghalaya, India",
        "source": "OpenStreetMap via OSMnx (Cleaned & Strongly Connected)",
        "download_method": "Point-based bounding box",
        "center_latitude": 25.42,
        "center_longitude": 91.82,
        "requested_distance_m": 25000,
        "raw_nodes": int(raw_nodes),
        "raw_directed_edges": int(raw_edges),
        "raw_weakly_connected_components": int(raw_wcc),
        "nodes": int(len(nodes)),
        "directed_edges": int(len(edges)),
        "weakly_connected_components": int(nx.number_weakly_connected_components(G)),
        "strongly_connected_components": int(nx.number_strongly_connected_components(G)),
        "bounds": {
            "min_lat": round(float(nodes["y"].min()), 6),
            "max_lat": round(float(nodes["y"].max()), 6),
            "min_lng": round(float(nodes["x"].min()), 6),
            "max_lng": round(float(nodes["x"].max()), 6),
        },
        "median_edge_length_m": round(float(edges["length"].median()), 2),
        "median_speed_kph": round(float(edges["speed_kph"].median()), 2),
        "missing_percent": {
            column: round(float(edges[column].isna().mean() * 100), 2)
            for column in ["highway", "maxspeed", "speed_kph", "travel_time", "length"]
            if column in edges.columns
        },
        "edge_attributes": list(edges.columns),
        "max_snap_distance_m": MAX_SNAP_DISTANCE_M,
        "location_coverage": location_checks,
        "validation_route_shillong_to_sohra": {
            "origin_node": shillong_node,
            "destination_node": sohra_node,
            "shortest_path_nodes": len(shortest_by_len),
            "shortest_path_distance_km": len_dist_km,
            "fastest_path_nodes": len(fastest_by_time),
            "fastest_path_distance_km": time_dist_km,
            "fastest_path_duration_min": fastest_duration_min,
        },
    }

    with open(AUDIT_REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\nROAD GRAPH PREPROCESSING & VALIDATION COMPLETE")
    print(json.dumps(report, indent=2))
    print(f"\nProcessed graph saved to: {PROCESSED_GRAPH_PATH}")
    print(f"Raw graph updated in-place: {RAW_GRAPH_PATH}")
    print(f"Updated audit saved to: {AUDIT_REPORT_PATH}")


if __name__ == "__main__":
    main()

