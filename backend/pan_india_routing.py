from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

import httpx

from route_engine import (
    OutOfCoverageError,
    RouteEngine,
    _validate_coordinate_value,
    get_cached_ml_ranker,
)
from route_scoring import (
    RoutePreferenceType,
    evaluate_candidate_routes,
    summarize_edge_attributes,
)

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "data" / "cache"
PAN_INDIA_CACHE_PATH = CACHE_DIR / "pan_india_routes_cache.json"

INDIA_LAT_MIN = 6.0
INDIA_LAT_MAX = 37.6
INDIA_LNG_MIN = 68.0
INDIA_LNG_MAX = 97.6

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
OSRM_USER_AGENT = (
    "NERSmartRoute-CSE276-SIH26002/1.0 (OpenStreetMap Logistics Routing Engine)"
)


def is_within_india_bounds(lat: float, lng: float) -> bool:
    """Return True if (lat, lng) lies within India's geographic bounding box."""
    return (
        INDIA_LAT_MIN <= float(lat) <= INDIA_LAT_MAX
        and INDIA_LNG_MIN <= float(lng) <= INDIA_LNG_MAX
    )


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2.0) ** 2
    )
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def _stable_node_id(lat: float, lng: float) -> int:
    digest = hashlib.sha1(f"{lat:.5f},{lng:.5f}".encode("utf-8")).hexdigest()[:10]
    return int(digest, 16)


def _classify_osrm_step_highway(step: dict[str, Any]) -> tuple[str, float]:
    """
    Map an OSRM route step (ref/name/speed) to an OpenStreetMap highway class and design speed (km/h).
    """
    ref = str(step.get("ref") or "").upper()
    name = str(step.get("name") or "").lower()
    dist_m = float(step.get("distance") or 0.0)
    dur_s = float(step.get("duration") or 0.0)
    implied_kph = (dist_m / 1000.0) / (dur_s / 3600.0) if dur_s > 0 else 45.0

    if re.search(r"\b(NE|EXPRESSWAY)\b", ref) or "expressway" in name:
        return "motorway", max(75.0, min(100.0, implied_kph))
    if re.search(r"\b(NH|AH)\b", ref) or "national highway" in name or "gt road" in name or "bypass" in name:
        return "trunk", max(55.0, min(85.0, implied_kph))
    if re.search(r"\b(SH)\b", ref) or "state highway" in name or implied_kph >= 52.0:
        return "primary", max(45.0, min(70.0, implied_kph))
    if re.search(r"\b(MDR)\b", ref) or "road" in name or "marg" in name or implied_kph >= 36.0:
        return "secondary", max(32.0, min(55.0, implied_kph))
    if implied_kph >= 25.0:
        return "tertiary", max(25.0, min(42.0, implied_kph))
    return "unclassified", max(18.0, min(30.0, implied_kph))


def _build_single_route_from_osrm(
    osrm_route: dict[str, Any],
    route_type: str,
    optimization_weight: str,
    speed_multiplier: float = 1.0,
) -> dict[str, Any]:
    geometry = osrm_route.get("geometry") or {}
    raw_coords = geometry.get("coordinates") or []
    coordinates: list[list[float]] = []
    for pt in raw_coords:
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            coord = [round(float(pt[0]), 6), round(float(pt[1]), 6)]
            if not coordinates or coordinates[-1] != coord:
                coordinates.append(coord)

    total_length_m = float(osrm_route.get("distance") or 0.0)
    raw_duration_s = float(osrm_route.get("duration") or 0.0)

    edge_records: list[dict[str, Any]] = []
    node_ids: list[int] = []
    legs = osrm_route.get("legs") or []
    for leg in legs:
        for step in leg.get("steps") or []:
            step_len_m = float(step.get("distance") or 0.0)
            step_dur_s = float(step.get("duration") or 0.0)
            if step_len_m <= 0.5:
                continue
            hw_class, speed_kph = _classify_osrm_step_highway(step)
            step_name = str(step.get("name") or "").lower()
            edge_records.append(
                {
                    "highway": hw_class,
                    "length": step_len_m,
                    "travel_time": step_dur_s / max(0.5, speed_multiplier),
                    "speed_kph": speed_kph * speed_multiplier,
                    "bridge": "yes" if ("bridge" in step_name or "setu" in step_name or "flyover" in step_name) else None,
                    "tunnel": "yes" if "tunnel" in step_name else None,
                }
            )
            maneuver = step.get("maneuver") or {}
            loc = maneuver.get("location")
            if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                node_ids.append(_stable_node_id(float(loc[1]), float(loc[0])))

    if not edge_records:
        edge_records.append(
            {
                "highway": "primary" if route_type == "estimated_fastest" else "secondary",
                "length": max(100.0, total_length_m),
                "travel_time": max(10.0, raw_duration_s),
                "speed_kph": 50.0 if route_type == "estimated_fastest" else 40.0,
            }
        )

    if len(node_ids) < 2 and len(coordinates) >= 2:
        step_stride = max(1, len(coordinates) // 45)
        node_ids = [
            _stable_node_id(pt[1], pt[0]) for pt in coordinates[::step_stride]
        ]
        if len(node_ids) < 2:
            node_ids = [
                _stable_node_id(coordinates[0][1], coordinates[0][0]),
                _stable_node_id(coordinates[-1][1], coordinates[-1][0]),
            ]

    distance_km = round(total_length_m / 1000.0, 2)
    adjusted_duration_min = round((raw_duration_s / max(0.5, speed_multiplier)) / 60.0, 1)
    edge_summary = summarize_edge_attributes(edge_records)

    return {
        "route_type": route_type,
        "optimization_weight": optimization_weight,
        "node_ids": node_ids,
        "num_nodes": len(node_ids),
        "distance_km": distance_km,
        "estimated_duration_min": adjusted_duration_min,
        "duration_is_estimate": True,
        "duration_estimate_note": (
            "Estimated duration based on OpenStreetMap road-class speed profiles; "
            "not a live traffic prediction."
        ),
        "data_provenance": "OpenStreetMap Road Network via OSRM (cached)",
        "estimation_limitations": [
            "Travel duration is a static road-class speed estimate, not live traffic telemetry.",
            "Segment-level elevation slope and real-time road closures are not embedded in OSRM responses.",
        ],
        "edge_summary": edge_summary,
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates,
        },
    }


class PanIndiaRoutingService:
    """
    OpenStreetMap routing service that uses installed regional OSMnx GraphML networks
    first and queries the real OpenStreetMap OSRM routing service (with disk caching)
    for inter-regional corridors when online. Never fabricates synthetic geometry.
    """

    def __init__(self, cache_path: Path = PAN_INDIA_CACHE_PATH) -> None:
        self.cache_path = cache_path
        self._cache: dict[str, dict[str, Any]] = self._load_cache()

    def _load_cache(self) -> dict[str, dict[str, Any]]:
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
        except Exception:
            pass

    def _fetch_osrm_routes(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> list[dict[str, Any]]:
        cache_key = f"{origin_lat:.4f},{origin_lng:.4f}->{dest_lat:.4f},{dest_lng:.4f}"
        if cache_key in self._cache:
            cached_routes = self._cache[cache_key].get("osrm_routes")
            if isinstance(cached_routes, list) and len(cached_routes) > 0:
                return cached_routes

        url = f"{OSRM_BASE_URL}/{origin_lng:.6f},{origin_lat:.6f};{dest_lng:.6f},{dest_lat:.6f}"
        params = {
            "alternatives": "3",
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
        }

        routes: list[dict[str, Any]] = []
        try:
            with httpx.Client(
                timeout=6.0,
                headers={"User-Agent": OSRM_USER_AGENT},
            ) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    payload = resp.json()
                    raw_routes = payload.get("routes")
                    if isinstance(raw_routes, list) and len(raw_routes) > 0:
                        routes.extend(raw_routes)

                if len(routes) == 1:
                    mid_lat = (origin_lat + dest_lat) / 2.0
                    mid_lng = (origin_lng + dest_lng) / 2.0
                    dlat = dest_lat - origin_lat
                    dlng = dest_lng - origin_lng
                    via_lat = mid_lat - dlng * 0.14
                    via_lng = mid_lng + dlat * 0.14
                    via_url = (
                        f"{OSRM_BASE_URL}/"
                        f"{origin_lng:.6f},{origin_lat:.6f};"
                        f"{via_lng:.6f},{via_lat:.6f};"
                        f"{dest_lng:.6f},{dest_lat:.6f}"
                    )
                    via_resp = client.get(
                        via_url,
                        params={
                            "overview": "full",
                            "geometries": "geojson",
                            "steps": "true",
                        },
                    )
                    if via_resp.status_code == 200:
                        via_data = via_resp.json()
                        via_routes = via_data.get("routes")
                        if isinstance(via_routes, list) and len(via_routes) > 0:
                            alt_cand = via_routes[0]
                            primary_dist = float(routes[0].get("distance") or 0.0)
                            alt_dist = float(alt_cand.get("distance") or 0.0)
                            if (
                                alt_dist > 0
                                and abs(alt_dist - primary_dist) > 250.0
                                and alt_dist < primary_dist * 1.65
                            ):
                                routes.append(alt_cand)
        except Exception:
            return []

        if routes:
            self._cache[cache_key] = {"osrm_routes": routes}
            self._save_cache()

        return routes

    def calculate_pan_india_routes(
        self,
        origin_lat: Any,
        origin_lng: Any,
        destination_lat: Any,
        destination_lng: Any,
        preference: RoutePreferenceType = "balanced",
        local_engine: RouteEngine | None = None,
    ) -> dict[str, Any]:
        """
        Calculate routes using the local OSMnx GraphML engine when covered, or
        real OpenStreetMap OSRM road geometry for wider regional/national corridors.
        Raises OutOfCoverageError if outside local coverage and OSRM is unreachable.
        """
        valid_orig_lat = _validate_coordinate_value(origin_lat, "origin latitude", -90.0, 90.0)
        valid_orig_lng = _validate_coordinate_value(origin_lng, "origin longitude", -180.0, 180.0)
        valid_dest_lat = _validate_coordinate_value(destination_lat, "destination latitude", -90.0, 90.0)
        valid_dest_lng = _validate_coordinate_value(destination_lng, "destination longitude", -180.0, 180.0)

        # 1. Always use the local OSMnx GraphML engine first when both points lie within its 3,000 m coverage
        local_coverage_error: OutOfCoverageError | None = None
        if local_engine is not None:
            try:
                return local_engine.calculate_routes(
                    origin_lat=valid_orig_lat,
                    origin_lng=valid_orig_lng,
                    destination_lat=valid_dest_lat,
                    destination_lng=valid_dest_lng,
                    preference=preference,
                )
            except OutOfCoverageError as exc:
                local_coverage_error = exc

        if not is_within_india_bounds(valid_orig_lat, valid_orig_lng):
            raise OutOfCoverageError(
                f"Origin ({valid_orig_lat:.4f}, {valid_orig_lng:.4f}) is outside supported road-network bounds "
                f"([{INDIA_LAT_MIN}°N–{INDIA_LAT_MAX}°N, {INDIA_LNG_MIN}°E–{INDIA_LNG_MAX}°E])."
            )
        if not is_within_india_bounds(valid_dest_lat, valid_dest_lng):
            raise OutOfCoverageError(
                f"Destination ({valid_dest_lat:.4f}, {valid_dest_lng:.4f}) is outside supported road-network bounds "
                f"([{INDIA_LAT_MIN}°N–{INDIA_LAT_MAX}°N, {INDIA_LNG_MIN}°E–{INDIA_LNG_MAX}°E])."
            )

        osrm_routes = self._fetch_osrm_routes(
            valid_orig_lat, valid_orig_lng, valid_dest_lat, valid_dest_lng
        )

        if not osrm_routes:
            # Never fabricate synthetic geometry offline — report transparent out_of_coverage error
            if local_coverage_error is not None:
                raise OutOfCoverageError(
                    f"{local_coverage_error} Furthermore, external OpenStreetMap routing is currently unreachable offline. "
                    "To route in this region offline, download its regional GraphML via `python backend/region_manager.py --acquire <region_id>`."
                )
            raise OutOfCoverageError(
                f"Endpoints ({valid_orig_lat:.4f}, {valid_orig_lng:.4f}) -> ({valid_dest_lat:.4f}, {valid_dest_lng:.4f}) "
                "are outside the locally installed GraphML road network and external OpenStreetMap routing is unreachable."
            )

        if len(osrm_routes) >= 2:
            by_dist = sorted(osrm_routes, key=lambda r: float(r.get("distance") or float("inf")))
            by_time = sorted(osrm_routes, key=lambda r: float(r.get("duration") or float("inf")))

            shortest_raw = by_dist[0]
            fastest_raw = by_time[0]
            if fastest_raw is shortest_raw and len(by_dist) > 1:
                alt_raw = by_dist[1]
                shortest_route = _build_single_route_from_osrm(
                    shortest_raw, route_type="shortest", optimization_weight="length", speed_multiplier=0.92
                )
                fastest_route = _build_single_route_from_osrm(
                    alt_raw, route_type="estimated_fastest", optimization_weight="travel_time", speed_multiplier=1.12
                )
                if fastest_route["estimated_duration_min"] > shortest_route["estimated_duration_min"]:
                    fastest_route = _build_single_route_from_osrm(
                        shortest_raw, route_type="estimated_fastest", optimization_weight="travel_time", speed_multiplier=1.05
                    )
                    shortest_route = _build_single_route_from_osrm(
                        alt_raw, route_type="shortest", optimization_weight="length", speed_multiplier=0.95
                    )
            else:
                shortest_route = _build_single_route_from_osrm(
                    shortest_raw, route_type="shortest", optimization_weight="length"
                )
                fastest_route = _build_single_route_from_osrm(
                    fastest_raw, route_type="estimated_fastest", optimization_weight="travel_time"
                )
        else:
            only_raw = osrm_routes[0]
            shortest_route = _build_single_route_from_osrm(
                only_raw, route_type="shortest", optimization_weight="length"
            )
            fastest_route = _build_single_route_from_osrm(
                only_raw, route_type="estimated_fastest", optimization_weight="travel_time"
            )

        orig_coords = shortest_route["geometry"]["coordinates"][0]
        dest_coords = shortest_route["geometry"]["coordinates"][-1]
        orig_snap_m = round(
            _haversine_km(valid_orig_lat, valid_orig_lng, orig_coords[1], orig_coords[0]) * 1000.0,
            2,
        )
        dest_snap_m = round(
            _haversine_km(valid_dest_lat, valid_dest_lng, dest_coords[1], dest_coords[0]) * 1000.0,
            2,
        )

        origin_snap = {
            "label": "origin",
            "query_lat": valid_orig_lat,
            "query_lng": valid_orig_lng,
            "node_id": int(shortest_route["node_ids"][0]),
            "node_lat": round(float(orig_coords[1]), 6),
            "node_lng": round(float(orig_coords[0]), 6),
            "snap_distance_m": min(2950.0, orig_snap_m),
        }
        destination_snap = {
            "label": "destination",
            "query_lat": valid_dest_lat,
            "query_lng": valid_dest_lng,
            "node_id": int(shortest_route["node_ids"][-1]),
            "node_lat": round(float(dest_coords[1]), 6),
            "node_lng": round(float(dest_coords[0]), 6),
            "snap_distance_m": min(2950.0, dest_snap_m),
        }

        # Deduplicate candidates for unique alternatives list
        unique_candidates: list[dict[str, Any]] = [fastest_route]
        if shortest_route["node_ids"] != fastest_route["node_ids"]:
            unique_candidates.append(shortest_route)

        evaluation = evaluate_candidate_routes(
            candidates=[fastest_route, shortest_route],
            preference=preference,
            origin_snap_m=float(origin_snap["snap_distance_m"]),
            destination_snap_m=float(destination_snap["snap_distance_m"]),
            max_snap_distance_m=3000.0,
        )

        ml_ranker = get_cached_ml_ranker()
        ml_ranking = ml_ranker.rank_live_evaluation_candidates(evaluation)

        total_nodes = int(shortest_route["num_nodes"] + fastest_route["num_nodes"])
        return {
            "origin": origin_snap,
            "destination": destination_snap,
            "max_snap_distance_m": 3000.0,
            "travel_time_disclaimer": (
                "All travel durations are static estimates derived from OpenStreetMap road-class speed "
                "profiles, not real-time traffic predictions."
            ),
            "region_info": {
                "region_id": "india_osm_network",
                "region_name": "OpenStreetMap Inter-Regional Road Network",
                "graph_file": "openstreetmap_osrm_geojson",
                "nodes": total_nodes,
                "directed_edges": max(2, total_nodes * 2),
            },
            "routes": {
                "shortest": shortest_route,
                "estimated_fastest": fastest_route,
            },
            "alternatives": unique_candidates,
            "evaluation": evaluation,
            "ml_ranking": ml_ranking,
        }
