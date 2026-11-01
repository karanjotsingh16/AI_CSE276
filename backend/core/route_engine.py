from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

import networkx as nx
import osmnx as ox

BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if Path(__file__).resolve().parent.name in ("core", "services", "scripts", "tests")
    else Path(__file__).resolve().parent
)
DEFAULT_PROCESSED_GRAPH_PATH = (
    BASE_DIR / "data" / "processed" / "shillong_roads_clean.graphml"
)
MAX_SNAP_DISTANCE_M = 3000.0

if TYPE_CHECKING:
    from services.disruptions_service import DisruptionsService
    from services.weather_service import WeatherService

from core.route_ranking_ml import PairwiseRouteRanker
from core.route_scoring import (
    RoutePreferenceType,
    evaluate_candidate_routes,
    summarize_edge_attributes,
)


@lru_cache(maxsize=1)
def get_cached_ml_ranker() -> PairwiseRouteRanker:
    """Initialize or load the experimental pairwise route ranker artifact."""
    return PairwiseRouteRanker.load_or_train(random_state=42)


@lru_cache(maxsize=1)
def get_cached_weather_service() -> Any:
    """Initialize and cache the live weather service."""
    from services.weather_service import WeatherService
    return WeatherService()


@lru_cache(maxsize=1)
def get_cached_disruptions_service() -> Any:
    """Initialize and cache the regional road disruptions service."""
    from services.disruptions_service import DisruptionsService
    return DisruptionsService()


class RouteEngineError(Exception):
    """Base exception for all route engine errors."""


class GraphFileNotFoundError(RouteEngineError, FileNotFoundError):
    """Raised when the processed GraphML file does not exist or cannot be loaded."""


class InvalidCoordinateError(RouteEngineError, ValueError):
    """Raised when latitude or longitude values are missing, non-numeric, or out of range."""


class OutOfCoverageError(RouteEngineError, ValueError):
    """Raised when a coordinate is farther than MAX_SNAP_DISTANCE_M from the road network."""


class UnreachableDestinationError(RouteEngineError, RuntimeError):
    """Raised when no directed path exists between the snapped origin and destination nodes."""


def _validate_coordinate_value(value: Any, name: str, min_val: float, max_val: float) -> float:
    """Validate that a coordinate component is a finite float within [min_val, max_val]."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidCoordinateError(
            f"Invalid {name}: expected a numeric value in [{min_val}, {max_val}], got {value!r} ({type(value).__name__})."
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidCoordinateError(
            f"Invalid {name}: value must be finite (not NaN or infinity), got {value!r}."
        )
    if numeric < min_val or numeric > max_val:
        raise InvalidCoordinateError(
            f"Invalid {name}: {numeric} is outside valid geographic bounds [{min_val}, {max_val}]."
        )
    return numeric


class RouteEngine:
    """
    Standalone route calculation engine for processed OpenStreetMap GraphML road networks.

    Loads the processed GraphML road network once per instance, validates and snaps
    coordinates within a strict maximum snapping distance, computes shortest
    (by length) and estimated fastest (by imputed travel_time) routes, extracts
    verifiable edge-level road-class evidence, and evaluates deterministic + experimental ML rankings.
    """

    def __init__(
        self,
        graph_path: str | Path = DEFAULT_PROCESSED_GRAPH_PATH,
        max_snap_distance_m: float = MAX_SNAP_DISTANCE_M,
        region_id: str = "meghalaya_shillong_sohra",
        region_name: str = "East & West Khasi Hills (Shillong–Sohra–Mairang–Dawki)",
    ) -> None:
        self.graph_path = Path(graph_path).resolve()
        self.max_snap_distance_m = float(max_snap_distance_m)
        self.region_id = region_id
        self.region_name = region_name
        self.load_count = 0
        self._graph: nx.MultiDiGraph = self._load_graph_once()

    def _load_graph_once(self) -> nx.MultiDiGraph:
        if not self.graph_path.exists() or not self.graph_path.is_file():
            raise GraphFileNotFoundError(
                f"Processed road graph file not found at: {self.graph_path}"
            )
        try:
            graph = ox.load_graphml(self.graph_path)
        except Exception as exc:
            raise GraphFileNotFoundError(
                f"Failed to load GraphML file at {self.graph_path}: {exc}"
            ) from exc

        if graph.number_of_nodes() == 0 or graph.number_of_edges() == 0:
            raise RouteEngineError(
                f"Loaded road graph at {self.graph_path} is empty "
                f"(nodes={graph.number_of_nodes()}, edges={graph.number_of_edges()})."
            )

        # Verify required precomputed edge attributes exist on the processed graph
        sample_u, sample_v, sample_data = next(iter(graph.edges(data=True)))
        for required_attr in ("length", "travel_time", "speed_kph"):
            if required_attr not in sample_data:
                raise RouteEngineError(
                    f"Processed graph at {self.graph_path} is missing required edge attribute "
                    f"{required_attr!r} on edge ({sample_u}, {sample_v}). Run preprocess_roads.py first."
                )

        self.load_count += 1
        return graph

    @property
    def graph(self) -> nx.MultiDiGraph:
        return self._graph

    def validate_and_snap(
        self,
        lat: Any,
        lng: Any,
        label: str = "location",
    ) -> dict[str, Any]:
        """
        Validate (lat, lng) and snap to the nearest road node in the loaded graph.
        Raises InvalidCoordinateError or OutOfCoverageError on failure.
        """
        valid_lat = _validate_coordinate_value(lat, f"{label} latitude", -90.0, 90.0)
        valid_lng = _validate_coordinate_value(lng, f"{label} longitude", -180.0, 180.0)

        node_id, snap_dist_m = ox.distance.nearest_nodes(
            self._graph,
            X=valid_lng,
            Y=valid_lat,
            return_dist=True,
        )
        snap_dist_m = float(snap_dist_m)

        if snap_dist_m > self.max_snap_distance_m:
            node_data = self._graph.nodes[node_id]
            raise OutOfCoverageError(
                f"{label.capitalize()} ({valid_lat:.4f}, {valid_lng:.4f}) is outside road network coverage: "
                f"nearest road node {int(node_id)} at ({float(node_data['y']):.4f}, {float(node_data['x']):.4f}) "
                f"is {snap_dist_m:.1f} m ({snap_dist_m / 1000.0:.2f} km) away, which exceeds the "
                f"{self.max_snap_distance_m:.0f} m maximum snapping distance."
            )

        node_data = self._graph.nodes[node_id]
        return {
            "label": label,
            "query_lat": valid_lat,
            "query_lng": valid_lng,
            "node_id": int(node_id),
            "node_lat": round(float(node_data["y"]), 6),
            "node_lng": round(float(node_data["x"]), 6),
            "snap_distance_m": round(snap_dist_m, 2),
        }

    @staticmethod
    def _select_min_edge_data(
        graph: nx.MultiDiGraph,
        u: int,
        v: int,
        weight_attr: str,
    ) -> dict[str, Any]:
        """Select the parallel edge between u and v that minimizes weight_attr."""
        parallel_edges = graph[u][v]
        return min(
            parallel_edges.values(),
            key=lambda edge_data: float(edge_data.get(weight_attr, float("inf"))),
        )

    def _build_route_metrics_and_geometry(
        self,
        node_sequence: list[int],
        weight_attr: str,
        route_type: str,
    ) -> dict[str, Any]:
        """
        Extract full LineString geometry in [longitude, latitude] order, total distance (km),
        estimated travel duration (minutes), and edge-level road-class composition from a
        sequence of graph nodes.
        """
        if not node_sequence:
            raise RouteEngineError("Cannot build route details from an empty node sequence.")

        total_length_m = 0.0
        total_travel_time_s = 0.0
        coordinates: list[list[float]] = []
        edge_records: list[dict[str, Any]] = []

        if len(node_sequence) == 1:
            only_node = self._graph.nodes[node_sequence[0]]
            pt = [round(float(only_node["x"]), 6), round(float(only_node["y"]), 6)]
            # GeoJSON LineString requires at least 2 positions
            coordinates = [pt, pt]
        else:
            for u, v in zip(node_sequence[:-1], node_sequence[1:]):
                edge_data = self._select_min_edge_data(self._graph, u, v, weight_attr)
                total_length_m += float(edge_data["length"])
                total_travel_time_s += float(edge_data["travel_time"])
                edge_records.append(edge_data)

                u_node = self._graph.nodes[u]
                v_node = self._graph.nodes[v]
                u_coord = [round(float(u_node["x"]), 6), round(float(u_node["y"]), 6)]
                v_coord = [round(float(v_node["x"]), 6), round(float(v_node["y"]), 6)]

                geom = edge_data.get("geometry")
                if geom is not None and hasattr(geom, "coords"):
                    segment_coords = [
                        [round(float(x), 6), round(float(y), 6)]
                        for x, y in geom.coords
                    ]
                    # Ensure segment coordinates are oriented from u to v
                    if len(segment_coords) >= 2:
                        dist_start_to_u = math.hypot(
                            segment_coords[0][0] - u_coord[0],
                            segment_coords[0][1] - u_coord[1],
                        )
                        dist_end_to_u = math.hypot(
                            segment_coords[-1][0] - u_coord[0],
                            segment_coords[-1][1] - u_coord[1],
                        )
                        if dist_end_to_u < dist_start_to_u:
                            segment_coords.reverse()
                else:
                    segment_coords = [u_coord, v_coord]

                for pt in segment_coords:
                    if not coordinates or coordinates[-1] != pt:
                        coordinates.append(pt)

        distance_km = round(total_length_m / 1000.0, 2)
        estimated_duration_min = round(total_travel_time_s / 60.0, 1)
        node_ids = [int(n) for n in node_sequence]
        edge_summary = summarize_edge_attributes(edge_records)

        return {
            "route_type": route_type,
            "optimization_weight": weight_attr,
            "node_ids": node_ids,
            "num_nodes": len(node_ids),
            "distance_km": distance_km,
            "estimated_duration_min": estimated_duration_min,
            "duration_is_estimate": True,
            "duration_estimate_note": (
                "Estimated duration based on pre-imputed mountain highway class speeds; "
                "not a live traffic prediction."
            ),
            "data_provenance": (
                f"OpenStreetMap via OSMnx GraphML ({self.graph_path.name}, region={self.region_id})"
            ),
            "estimation_limitations": [
                "Travel duration is a static estimate from road-class speed imputation (15–45 km/h), not live traffic.",
                "99.81% of OpenStreetMap edges in the Shillong–Sohra region lack explicit maxspeed tags.",
                "Segment-level elevation slope and unverified road closures are not embedded in base travel_time.",
            ],
            "edge_summary": edge_summary,
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates,
            },
        }

    def _compute_single_route(
        self,
        origin_node: int,
        destination_node: int,
        weight_attr: str,
        route_type: str,
    ) -> dict[str, Any]:
        try:
            node_sequence = nx.shortest_path(
                self._graph,
                source=origin_node,
                target=destination_node,
                weight=weight_attr,
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
            raise UnreachableDestinationError(
                f"No directed road path exists from origin node {origin_node} "
                f"to destination node {destination_node} (weight={weight_attr!r})."
            ) from exc

        return self._build_route_metrics_and_geometry(
            node_sequence=node_sequence,
            weight_attr=weight_attr,
            route_type=route_type,
        )

    def _compute_penalized_alternative_route(
        self,
        origin_node: int,
        destination_node: int,
        primary_routes: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Compute a genuinely distinct 3rd candidate corridor by penalizing interior edges
        already traversed by the shortest and estimated-fastest paths.
        Returns None if no distinct path exists or if origin == destination.
        """
        if origin_node == destination_node:
            return None

        penalized_edges: set[tuple[int, int]] = set()
        existing_node_sets: list[set[int]] = []
        for route in primary_routes:
            nids = [int(n) for n in route.get("node_ids", [])]
            if len(nids) >= 2:
                existing_node_sets.append(set(nids))
                # Penalize interior edges (preserve immediate access edges near origin/destination)
                trim = min(4, max(1, len(nids) // 12))
                core_nodes = nids[trim:-trim] if len(nids) > 2 * trim + 1 else nids
                for u, v in zip(core_nodes[:-1], core_nodes[1:]):
                    penalized_edges.add((u, v))

        if not penalized_edges:
            return None

        def _penalized_weight(u: int, v: int, edge_dict: dict[str, Any]) -> float:
            # MultiDiGraph passes dict of parallel edges {key: attr_dict} to weight callable in NetworkX
            best_t = min(
                float(data.get("travel_time", 1.0))
                for data in edge_dict.values()
            )
            return best_t * (2.4 if (u, v) in penalized_edges else 1.0)

        try:
            alt_sequence = nx.shortest_path(
                self._graph,
                source=origin_node,
                target=destination_node,
                weight=_penalized_weight,
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        alt_set = set(int(n) for n in alt_sequence)
        for existing_set in existing_node_sets:
            overlap_ratio = len(alt_set & existing_set) / max(1, len(alt_set | existing_set))
            if overlap_ratio > 0.85:
                return None

        return self._build_route_metrics_and_geometry(
            node_sequence=alt_sequence,
            weight_attr="travel_time",
            route_type="alternative_corridor",
        )

    @staticmethod
    def deduplicate_candidate_routes(
        routes_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Deduplicate candidate routes that share the exact same sequence of road nodes
        so identical paths are never returned as separate alternatives.
        """
        unique: list[dict[str, Any]] = []
        seen_by_nodes: dict[tuple[int, ...], dict[str, Any]] = {}
        for route in routes_list:
            key = tuple(int(n) for n in route.get("node_ids", []))
            if key in seen_by_nodes:
                existing = seen_by_nodes[key]
                merged = list(existing.get("merged_route_types", [existing["route_type"]]))
                if route["route_type"] not in merged:
                    merged.append(route["route_type"])
                existing["merged_route_types"] = merged
            else:
                copy_route = dict(route)
                copy_route["merged_route_types"] = [route["route_type"]]
                seen_by_nodes[key] = copy_route
                unique.append(copy_route)
        return unique

    def calculate_routes(
        self,
        origin_lat: Any,
        origin_lng: Any,
        destination_lat: Any,
        destination_lng: Any,
        preference: RoutePreferenceType = "balanced",
    ) -> dict[str, Any]:
        """
        Validate and snap origin and destination coordinates, then compute:
          1. Shortest route (minimizing edge 'length')
          2. Estimated fastest route (minimizing edge 'travel_time')
          3. Explainable deterministic route evaluation & component scores
          4. Separate experimental pairwise ML ranking comparison metadata
        """
        origin_snap = self.validate_and_snap(origin_lat, origin_lng, label="origin")
        destination_snap = self.validate_and_snap(
            destination_lat, destination_lng, label="destination"
        )

        shortest_route = self._compute_single_route(
            origin_node=origin_snap["node_id"],
            destination_node=destination_snap["node_id"],
            weight_attr="length",
            route_type="shortest",
        )
        fastest_route = self._compute_single_route(
            origin_node=origin_snap["node_id"],
            destination_node=destination_snap["node_id"],
            weight_attr="travel_time",
            route_type="estimated_fastest",
        )

        alt_route = self._compute_penalized_alternative_route(
            origin_node=origin_snap["node_id"],
            destination_node=destination_snap["node_id"],
            primary_routes=[fastest_route, shortest_route],
        )

        raw_candidates = [fastest_route, shortest_route]
        if alt_route is not None:
            raw_candidates.append(alt_route)
        unique_alternatives = self.deduplicate_candidate_routes(raw_candidates)

        # Evaluate live corridor weather and verified road disruptions
        weather_svc = get_cached_weather_service()
        disruptions_svc = get_cached_disruptions_service()

        weather_evals: dict[str, dict[str, Any]] = {}
        disruption_evals: dict[str, dict[str, Any]] = {}

        for r_cand in raw_candidates:
            geom_coords = r_cand.get("geometry", {}).get("coordinates", [])
            r_type = str(r_cand.get("route_type", "candidate"))
            w_res = weather_svc.evaluate_route_corridor_weather(geom_coords)
            d_res = disruptions_svc.evaluate_route_disruptions(geom_coords)
            weather_evals[r_type] = w_res
            disruption_evals[r_type] = d_res
            r_cand["weather"] = w_res
            r_cand["disruptions"] = d_res

        evaluation = evaluate_candidate_routes(
            candidates=raw_candidates,
            preference=preference,
            origin_snap_m=float(origin_snap["snap_distance_m"]),
            destination_snap_m=float(destination_snap["snap_distance_m"]),
            max_snap_distance_m=self.max_snap_distance_m,
            weather_evaluations=weather_evals,
            disruption_evaluations=disruption_evals,
        )

        ml_ranker = get_cached_ml_ranker()
        ml_ranking = ml_ranker.rank_live_evaluation_candidates(evaluation)

        routes_dict: dict[str, Any] = {
            "shortest": shortest_route,
            "estimated_fastest": fastest_route,
        }
        if alt_route is not None:
            routes_dict["alternative_corridor"] = alt_route

        # Primary route summaries for convenient top-level access
        rec_id = evaluation.get("recommended_route_id", "estimated_fastest")
        primary_w = weather_evals.get(str(rec_id)) or weather_evals.get("estimated_fastest")
        primary_d = disruption_evals.get(str(rec_id)) or disruption_evals.get("estimated_fastest")

        return {
            "origin": origin_snap,
            "destination": destination_snap,
            "max_snap_distance_m": self.max_snap_distance_m,
            "travel_time_disclaimer": (
                "All travel durations are static estimates derived from road-class speed "
                "imputation, not real-time traffic predictions."
            ),
            "region_info": {
                "region_id": self.region_id,
                "region_name": self.region_name,
                "graph_file": self.graph_path.name,
                "nodes": int(self._graph.number_of_nodes()),
                "directed_edges": int(self._graph.number_of_edges()),
            },
            "routes": routes_dict,
            "alternatives": unique_alternatives,
            "evaluation": evaluation,
            "ml_ranking": ml_ranking,
            "weather_summary": primary_w,
            "disruptions_summary": primary_d,
        }
