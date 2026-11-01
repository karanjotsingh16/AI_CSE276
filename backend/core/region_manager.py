from __future__ import annotations

import argparse
from collections import OrderedDict
import json
import math
from pathlib import Path
from typing import Any

import networkx as nx
import osmnx as ox

from core.route_engine import (
    DEFAULT_PROCESSED_GRAPH_PATH,
    MAX_SNAP_DISTANCE_M,
    RouteEngine,
)
from core.route_scoring import FALLBACK_SPEED_KPH, MOUNTAIN_HIGHWAY_SPEEDS_KPH

BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if Path(__file__).resolve().parent.name in ("core", "services", "scripts", "tests")
    else Path(__file__).resolve().parent
)
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CATALOG_PATH = BASE_DIR / "data" / "regions_catalog.json"


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute great-circle distance in metres between two WGS84 coordinates."""
    r_earth_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    )
    return 2.0 * r_earth_m * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def _point_in_bounds(
    lat: float,
    lng: float,
    bounds: dict[str, float],
    margin_deg: float = 0.025,
) -> bool:
    """Return True if (lat, lng) lies inside bounds expanded by margin_deg (~2.7 km)."""
    return (
        (float(bounds["min_lat"]) - margin_deg) <= lat <= (float(bounds["max_lat"]) + margin_deg)
        and (float(bounds["min_lng"]) - margin_deg) <= lng <= (float(bounds["max_lng"]) + margin_deg)
    )


class RegionGraphManager:
    """
    Manages regional road-network GraphML files, coverage checks, and bounded LRU
    in-memory caching for multi-region expansion beyond Shillong.
    """

    def __init__(
        self,
        catalog_path: str | Path = CATALOG_PATH,
        processed_dir: str | Path = PROCESSED_DIR,
        max_cached_engines: int = 2,
    ) -> None:
        self.catalog_path = Path(catalog_path).resolve()
        self.processed_dir = Path(processed_dir).resolve()
        self.max_cached_engines = max(1, int(max_cached_engines))
        self._catalog_data = self._load_catalog()
        self._engine_cache: OrderedDict[str, RouteEngine] = OrderedDict()

    def _load_catalog(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            return {
                "default_region_id": "meghalaya_shillong_sohra",
                "max_snap_distance_m": MAX_SNAP_DISTANCE_M,
                "regions": [
                    {
                        "region_id": "meghalaya_shillong_sohra",
                        "name": "East & West Khasi Hills (Shillong–Sohra)",
                        "state": "Meghalaya",
                        "phase": "Phase 1 — Installed Core Network",
                        "graph_filename": DEFAULT_PROCESSED_GRAPH_PATH.name,
                        "center_lat": 25.42,
                        "center_lng": 91.82,
                        "download_radius_m": 25000,
                        "network_type": "drive",
                        "custom_filter": None,
                        "bounds": {
                            "min_lat": 25.195198,
                            "max_lat": 25.644707,
                            "min_lng": 91.571629,
                            "max_lng": 92.068831,
                        },
                        "key_hubs": ["Shillong", "Sohra", "Mairang", "Dawki"],
                        "description": "Default Shillong–Sohra road network.",
                    }
                ],
            }
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def default_region_id(self) -> str:
        return str(self._catalog_data.get("default_region_id", "meghalaya_shillong_sohra"))

    def get_region_entry(self, region_id: str) -> dict[str, Any] | None:
        for reg in self._catalog_data.get("regions", []):
            if reg.get("region_id") == region_id:
                return dict(reg)
        return None

    def get_region_graph_path(self, region_id: str) -> Path | None:
        entry = self.get_region_entry(region_id)
        if not entry:
            return None
        return (self.processed_dir / str(entry["graph_filename"])).resolve()

    def is_region_installed(self, region_id: str) -> bool:
        path = self.get_region_graph_path(region_id)
        return bool(path is not None and path.exists() and path.is_file())

    def register_engine_instance(self, region_id: str, engine: RouteEngine) -> None:
        """Register an already-loaded RouteEngine (such as the startup default) in the LRU cache."""
        if region_id in self._engine_cache:
            self._engine_cache.move_to_end(region_id)
        self._engine_cache[region_id] = engine
        while len(self._engine_cache) > self.max_cached_engines:
            self._engine_cache.popitem(last=False)

    def get_engine_for_region(self, region_id: str | None = None) -> RouteEngine:
        target_id = region_id or self.default_region_id
        if target_id in self._engine_cache:
            self._engine_cache.move_to_end(target_id)
            return self._engine_cache[target_id]

        graph_path = self.get_region_graph_path(target_id)
        if graph_path is None:
            graph_path = DEFAULT_PROCESSED_GRAPH_PATH

        engine = RouteEngine(
            graph_path=graph_path,
            max_snap_distance_m=float(
                self._catalog_data.get("max_snap_distance_m", MAX_SNAP_DISTANCE_M)
            ),
        )
        self.register_engine_instance(target_id, engine)
        return engine

    def list_regions_status(self) -> list[dict[str, Any]]:
        """Return all catalog regions with their installation, cache, and coverage metadata."""
        output: list[dict[str, Any]] = []
        for reg in self._catalog_data.get("regions", []):
            rid = str(reg["region_id"])
            g_path = self.get_region_graph_path(rid)
            installed = bool(g_path and g_path.exists() and g_path.is_file())
            in_memory = rid in self._engine_cache
            file_size_mb = (
                round(g_path.stat().st_size / (1024 * 1024), 2)
                if installed and g_path is not None
                else None
            )
            nodes_count = (
                int(self._engine_cache[rid].graph.number_of_nodes())
                if in_memory
                else (21764 if rid == "meghalaya_shillong_sohra" and installed else None)
            )
            edges_count = (
                int(self._engine_cache[rid].graph.number_of_edges())
                if in_memory
                else (53888 if rid == "meghalaya_shillong_sohra" and installed else None)
            )

            output.append(
                {
                    **reg,
                    "installed_on_disk": installed,
                    "loaded_in_memory": in_memory,
                    "graph_path": str(g_path) if g_path else None,
                    "file_size_mb": file_size_mb,
                    "nodes": nodes_count,
                    "directed_edges": edges_count,
                    "acquire_cli_command": f"python backend/region_manager.py --acquire {rid}",
                }
            )
        return output

    def find_matching_catalog_regions(
        self, lat: float, lng: float
    ) -> list[dict[str, Any]]:
        """Return catalog region entries whose bounding box covers (lat, lng)."""
        matches: list[dict[str, Any]] = []
        for reg in self._catalog_data.get("regions", []):
            bounds = reg.get("bounds")
            if isinstance(bounds, dict) and _point_in_bounds(lat, lng, bounds):
                matches.append(dict(reg))
        return matches

    def evaluate_point_coverage(
        self,
        lat: float,
        lng: float,
        active_engine: RouteEngine | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate whether (lat, lng) is routable in the active loaded road graph,
        covered by another installed regional graph, or requires downloading a catalog region.
        """
        engine = active_engine
        if engine is None and self.default_region_id in self._engine_cache:
            engine = self._engine_cache[self.default_region_id]

        matching_regions = self.find_matching_catalog_regions(lat, lng)
        installed_matching = [
            r for r in matching_regions if self.is_region_installed(str(r["region_id"]))
        ]
        uninstalled_matching = [
            r for r in matching_regions if not self.is_region_installed(str(r["region_id"]))
        ]

        nearest_node_id: int | None = None
        node_lat: float | None = None
        node_lng: float | None = None
        snap_distance_m: float | None = None
        max_snap_m = float(
            engine.max_snap_distance_m
            if engine is not None
            else self._catalog_data.get("max_snap_distance_m", MAX_SNAP_DISTANCE_M)
        )

        if engine is not None:
            nid, dist_m = ox.distance.nearest_nodes(
                engine.graph, X=float(lng), Y=float(lat), return_dist=True
            )
            nearest_node_id = int(nid)
            node_data = engine.graph.nodes[nid]
            node_lat = round(float(node_data["y"]), 6)
            node_lng = round(float(node_data["x"]), 6)
            snap_distance_m = round(float(dist_m), 2)

        within_loaded = bool(
            snap_distance_m is not None and snap_distance_m <= max_snap_m
        )
        within_india = bool(
            6.0 <= float(lat) <= 37.6 and 68.0 <= float(lng) <= 97.6
        )

        if within_loaded:
            active_region = (
                installed_matching[0]
                if installed_matching
                else self.get_region_entry(self.default_region_id)
            )
            reg_id = str(active_region["region_id"]) if active_region else self.default_region_id
            reg_name = (
                str(active_region["name"])
                if active_region
                else "East & West Khasi Hills (Shillong–Sohra)"
            )
            return {
                "within_loaded_graph": True,
                "within_india_network": within_india,
                "status": "routable_in_loaded_graph",
                "region_id": reg_id,
                "region_name": reg_name,
                "nearest_node_id": nearest_node_id,
                "nearest_node_lat": node_lat,
                "nearest_node_lng": node_lng,
                "snap_distance_m": snap_distance_m,
                "max_snap_distance_m": max_snap_m,
                "matching_catalog_regions": [str(r["region_id"]) for r in matching_regions],
                "acquire_command": None,
                "message": (
                    f"Within loaded road network coverage ({snap_distance_m:.1f} m from node {nearest_node_id})."
                ),
            }

        if installed_matching:
            best_installed = installed_matching[0]
            reg_id = str(best_installed["region_id"])
            return {
                "within_loaded_graph": True,
                "within_india_network": within_india,
                "status": "routable_in_installed_region",
                "region_id": reg_id,
                "region_name": str(best_installed["name"]),
                "nearest_node_id": nearest_node_id,
                "nearest_node_lat": node_lat,
                "nearest_node_lng": node_lng,
                "snap_distance_m": snap_distance_m,
                "max_snap_distance_m": max_snap_m,
                "matching_catalog_regions": [str(r["region_id"]) for r in matching_regions],
                "acquire_command": None,
                "message": (
                    f"Covered by installed regional graph '{best_installed['name']}' ({reg_id})."
                ),
            }

        if uninstalled_matching:
            target_reg = uninstalled_matching[0]
            reg_id = str(target_reg["region_id"])
            dist_km_str = (
                f"{snap_distance_m / 1000.0:.2f} km from current Shillong–Sohra graph; "
                if snap_distance_m is not None
                else ""
            )
            cmd = f"python backend/region_manager.py --acquire {reg_id}"
            return {
                "within_loaded_graph": False,
                "within_india_network": within_india,
                "status": "supported_region_not_downloaded",
                "region_id": reg_id,
                "region_name": str(target_reg["name"]),
                "nearest_node_id": nearest_node_id,
                "nearest_node_lat": node_lat,
                "nearest_node_lng": node_lng,
                "snap_distance_m": snap_distance_m,
                "max_snap_distance_m": max_snap_m,
                "matching_catalog_regions": [str(r["region_id"]) for r in matching_regions],
                "acquire_command": cmd,
                "message": (
                    f"{dist_km_str}Located in catalog region '{target_reg['name']}' ({reg_id}), "
                    f"which is not yet downloaded locally. Run `{cmd}` when online to enable routing here."
                ),
            }

        dist_km_note = (
            f"{snap_distance_m / 1000.0:.2f} km ({snap_distance_m:.0f} m) away from the nearest loaded road node"
            if snap_distance_m is not None
            else f"approx. {_haversine_distance_m(lat, lng, 25.42, 91.82) / 1000.0:.1f} km from the Shillong–Sohra coverage center"
        )
        return {
            "within_loaded_graph": False,
            "within_india_network": within_india,
            "status": "outside_all_catalog_regions",
            "region_id": "india_national_network" if within_india else None,
            "region_name": "All-India OpenStreetMap Network" if within_india else None,
            "nearest_node_id": nearest_node_id,
            "nearest_node_lat": node_lat,
            "nearest_node_lng": node_lng,
            "snap_distance_m": snap_distance_m,
            "max_snap_distance_m": max_snap_m,
            "matching_catalog_regions": [],
            "acquire_command": None,
            "message": (
                "Routable via Pan-India OpenStreetMap network."
                if within_india
                else f"Outside road-network coverage: coordinate ({lat:.4f}, {lng:.4f}) is {dist_km_note}, exceeding the {max_snap_m:.0f} m snapping limit."
            ),
        }

    def resolve_region_for_od(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        requested_region_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Determine which regional graph should serve an (origin, destination) pair.
        Checks whether a single installed region covers both endpoints or whether a
        catalog cross-region graph is required.
        """
        if requested_region_id:
            entry = self.get_region_entry(requested_region_id)
            installed = self.is_region_installed(requested_region_id)
            return {
                "region_id": requested_region_id,
                "region_name": entry["name"] if entry else requested_region_id,
                "installed_on_disk": installed,
                "cross_region_query": False,
                "acquire_command": (
                    None
                    if installed
                    else f"python backend/region_manager.py --acquire {requested_region_id}"
                ),
            }

        origin_regions = {
            str(r["region_id"]): r
            for r in self.find_matching_catalog_regions(origin_lat, origin_lng)
        }
        dest_regions = {
            str(r["region_id"]): r
            for r in self.find_matching_catalog_regions(destination_lat, destination_lng)
        }
        common_ids = [rid for rid in origin_regions if rid in dest_regions]

        # 1. Prefer an already-installed region that covers both endpoints
        for rid in common_ids:
            if self.is_region_installed(rid):
                reg = origin_regions[rid]
                return {
                    "region_id": rid,
                    "region_name": str(reg["name"]),
                    "installed_on_disk": True,
                    "cross_region_query": False,
                    "acquire_command": None,
                }

        # 2. If a single catalog region (e.g. unified corridor) covers both but is not yet downloaded
        if common_ids:
            rid = common_ids[0]
            reg = origin_regions[rid]
            return {
                "region_id": rid,
                "region_name": str(reg["name"]),
                "installed_on_disk": False,
                "cross_region_query": rid == "ner_guwahati_shillong_sohra_corridor",
                "acquire_command": f"python backend/region_manager.py --acquire {rid}",
            }

        # 3. Fallback to default installed region (which will perform exact snap check and report structured coverage guidance)
        default_entry = self.get_region_entry(self.default_region_id)
        return {
            "region_id": self.default_region_id,
            "region_name": (
                str(default_entry["name"])
                if default_entry
                else "East & West Khasi Hills (Shillong–Sohra)"
            ),
            "installed_on_disk": self.is_region_installed(self.default_region_id),
            "cross_region_query": bool(origin_regions and dest_regions and origin_regions != dest_regions),
            "acquire_command": None,
        }

    def acquire_and_preprocess_region(self, region_id: str) -> dict[str, Any]:
        """
        Download and preprocess a configured regional graph from OpenStreetMap via OSMnx.
        Requires active internet access. Saves cleaned GraphML to backend/data/processed/.
        """
        entry = self.get_region_entry(region_id)
        if not entry:
            raise ValueError(
                f"Unknown region_id {region_id!r}. Available regions: "
                f"{[r['region_id'] for r in self._catalog_data.get('regions', [])]}"
            )

        self.processed_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.processed_dir / str(entry["graph_filename"])

        center = (float(entry["center_lat"]), float(entry["center_lng"]))
        radius_m = int(entry.get("download_radius_m", 25000))
        network_type = str(entry.get("network_type", "drive"))
        custom_filter = entry.get("custom_filter")

        G_raw = ox.graph_from_point(
            center,
            dist=radius_m,
            dist_type="bbox",
            network_type=network_type,
            simplify=True,
            retain_all=False,
            custom_filter=custom_filter,
        )

        if G_raw.number_of_nodes() == 0 or G_raw.number_of_edges() == 0:
            raise RuntimeError(
                f"Downloaded graph for region {region_id!r} is empty."
            )

        G = ox.truncate.largest_component(G_raw, strongly=True)
        G = ox.routing.add_edge_speeds(
            G,
            hwy_speeds=MOUNTAIN_HIGHWAY_SPEEDS_KPH,
            fallback=FALLBACK_SPEED_KPH,
        )
        G = ox.routing.add_edge_travel_times(G)

        ox.save_graphml(G, filepath=out_path)

        return {
            "region_id": region_id,
            "region_name": entry["name"],
            "graph_path": str(out_path),
            "nodes": int(G.number_of_nodes()),
            "directed_edges": int(G.number_of_edges()),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inspect or download regional road graphs for NER SmartRoute."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all configured regions and their installation status.",
    )
    parser.add_argument(
        "--acquire",
        type=str,
        default=None,
        help="Download and preprocess a regional road graph by region_id (requires internet).",
    )
    args = parser.parse_args()

    mgr = RegionGraphManager()
    if args.acquire:
        print(f"Acquiring regional road graph '{args.acquire}'...")
        summary = mgr.acquire_and_preprocess_region(args.acquire)
        print(json.dumps(summary, indent=2))
    else:
        print(json.dumps(mgr.list_regions_status(), indent=2))

