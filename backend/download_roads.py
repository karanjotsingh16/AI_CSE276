from pathlib import Path
import json

import networkx as nx
import osmnx as ox

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
REPORT_DIR = BASE_DIR / "reports"

RAW_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Approximate centre of the Shillong–Sohra region.
# Coordinates are (latitude, longitude).
CENTER = (25.42, 91.82)
DISTANCE_METRES = 25000

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

print("Downloading the road network around Shillong, Meghalaya...")
print(f"Centre: {CENTER}")
print(f"Download area: approximately {DISTANCE_METRES / 1000:.0f} km")
print("This requires an internet connection and may take a few minutes.")

G = ox.graph_from_point(
    CENTER,
    dist=DISTANCE_METRES,
    dist_type="bbox",
    network_type="drive",
    simplify=True,
    retain_all=False,
)

if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
    raise RuntimeError(
        "The road network is empty. Check your internet connection and try again."
    )

# Retain the largest strongly connected component and impute mountain road speeds & travel times
G = ox.truncate.largest_component(G, strongly=True)
G = ox.routing.add_edge_speeds(
    G,
    hwy_speeds=MOUNTAIN_HIGHWAY_SPEEDS_KPH,
    fallback=25.0,
)
G = ox.routing.add_edge_travel_times(G)

graph_path = RAW_DIR / "shillong_roads.graphml"
ox.save_graphml(G, filepath=graph_path)

nodes, edges = ox.graph_to_gdfs(G)

report = {
    "region": "Shillong–Sohra region, Meghalaya, India",
    "source": "OpenStreetMap via OSMnx",
    "download_method": "Point-based bounding box",
    "center_latitude": CENTER[0],
    "center_longitude": CENTER[1],
    "requested_distance_m": DISTANCE_METRES,
    "nodes": int(len(nodes)),
    "directed_edges": int(len(edges)),
    "weakly_connected_components": int(
        nx.number_weakly_connected_components(G)
    ),
    "strongly_connected_components": int(
        nx.number_strongly_connected_components(G)
    ),
    "median_edge_length_m": round(float(edges["length"].median()), 2),
    "median_speed_kph": round(float(edges["speed_kph"].median()), 2),
    "missing_percent": {
        column: round(float(edges[column].isna().mean() * 100), 2)
        for column in ["highway", "maxspeed", "speed_kph", "travel_time", "length"]
        if column in edges.columns
    },
    "edge_attributes": list(edges.columns),
}

report_path = REPORT_DIR / "road_data_audit.json"

with open(report_path, "w", encoding="utf-8") as file:
    json.dump(report, file, indent=2)

print("\nROAD DATA DOWNLOAD COMPLETE")
print(json.dumps(report, indent=2))
print(f"\nGraph saved to: {graph_path}")
print(f"Audit saved to: {report_path}")
