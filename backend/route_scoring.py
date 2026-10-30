from __future__ import annotations

import math
from typing import Any, Literal

RoutePreferenceType = Literal["shortest", "fastest", "balanced", "accessibility"]

# Imputed mountain highway design speeds (km/h) matching preprocess_roads.py
MOUNTAIN_HIGHWAY_SPEEDS_KPH: dict[str, float] = {
    "motorway": 50.0,
    "motorway_link": 40.0,
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
    "service": 15.0,
}
FALLBACK_SPEED_KPH = 25.0
MIN_DESIGN_SPEED_KPH = 15.0
MAX_DESIGN_SPEED_KPH = 45.0

MAJOR_ARTERIAL_CLASSES = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
}
SECONDARY_COLLECTOR_CLASSES = {
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
}
LOCAL_UNCLASSIFIED_CLASSES = {
    "unclassified",
    "residential",
    "living_street",
    "service",
    "road",
}

PREFERENCE_WEIGHTS: dict[RoutePreferenceType, dict[str, Any]] = {
    "shortest": {
        "preference": "shortest",
        "label": "Shortest Distance",
        "distance": 1.00,
        "time": 0.00,
        "road_hierarchy": 0.00,
        "formula": "S_overall = 1.00 * S_distance + 0.00 * S_time + 0.00 * S_hierarchy",
    },
    "fastest": {
        "preference": "fastest",
        "label": "Fastest Estimated Time",
        "distance": 0.00,
        "time": 1.00,
        "road_hierarchy": 0.00,
        "formula": "S_overall = 0.00 * S_distance + 1.00 * S_time + 0.00 * S_hierarchy",
    },
    "balanced": {
        "preference": "balanced",
        "label": "Balanced (Distance + Est. Time + Road Class)",
        "distance": 0.45,
        "time": 0.45,
        "road_hierarchy": 0.10,
        "formula": "S_overall = 0.45 * S_distance + 0.45 * S_time + 0.10 * S_hierarchy",
    },
    "accessibility": {
        "preference": "accessibility",
        "label": "Accessibility-Focused (Arterial Hierarchy + Time + Distance)",
        "distance": 0.25,
        "time": 0.35,
        "road_hierarchy": 0.40,
        "formula": "S_overall = 0.25 * S_distance + 0.35 * S_time + 0.40 * S_hierarchy (verified disruption/weather sub-scores marked unavailable)",
    },
}

DEFAULT_LIMITATIONS_AND_UNAVAILABLE_CRITERIA: list[str] = [
    "Speed limits (maxspeed) are missing on 99.81% of OpenStreetMap edges in the Shillong–Sohra region; travel durations rely on static mountain highway class speed imputation (15–45 km/h).",
    "Live traffic congestion, accident/landslide probability, and 30 m DEM elevation slope are unavailable in the backend dataset and are excluded from route scoring.",
    "Synthetic K-Means demand zones (data_source='synthetic_demo') are excluded from the primary route recommendation score so synthetic demonstration points do not distort real road routing.",
]


def _round1(val: float) -> float:
    return round(float(val), 1)


def _round2(val: float) -> float:
    return round(float(val), 2)


def _clamp(val: float, low: float = 0.0, high: float = 100.0) -> float:
    if not math.isfinite(val):
        return low
    return max(low, min(high, val))


def normalize_highway_tag(raw_tag: Any) -> tuple[str, bool]:
    """
    Normalize an OSMnx edge 'highway' attribute (which may be a str, list[str], or None).
    Returns (normalized_class_str, was_missing_or_imputed).
    """
    if raw_tag is None:
        return "unclassified", True

    if isinstance(raw_tag, (list, tuple, set)):
        items = [str(x).strip().lower() for x in raw_tag if x is not None and str(x).strip()]
        if not items:
            return "unclassified", True
        # When OSMnx simplifies edges with multiple tags, select the highest-speed class
        best = max(
            items,
            key=lambda h: MOUNTAIN_HIGHWAY_SPEEDS_KPH.get(h, FALLBACK_SPEED_KPH),
        )
        return best, best not in MOUNTAIN_HIGHWAY_SPEEDS_KPH

    if isinstance(raw_tag, str):
        cleaned = raw_tag.strip().lower()
        if not cleaned:
            return "unclassified", True
        # Handle stringified list representation e.g. "['primary', 'secondary']"
        if cleaned.startswith("[") and cleaned.endswith("]"):
            inner = [
                part.strip(" '\"")
                for part in cleaned[1:-1].split(",")
                if part.strip(" '\"")
            ]
            if inner:
                best = max(
                    inner,
                    key=lambda h: MOUNTAIN_HIGHWAY_SPEEDS_KPH.get(h, FALLBACK_SPEED_KPH),
                )
                return best, best not in MOUNTAIN_HIGHWAY_SPEEDS_KPH
        return cleaned, cleaned not in MOUNTAIN_HIGHWAY_SPEEDS_KPH

    return "unclassified", True


def _is_truthy_structure_tag(raw_tag: Any) -> bool:
    """Return True if an OSM 'bridge' or 'tunnel' tag indicates a structure is present."""
    if raw_tag is None or raw_tag is False:
        return False
    if isinstance(raw_tag, (list, tuple, set)):
        return any(_is_truthy_structure_tag(x) for x in raw_tag)
    val = str(raw_tag).strip().lower()
    return val not in ("", "no", "false", "0", "none", "nan")


def _has_observed_maxspeed(raw_tag: Any) -> bool:
    """Return True if an OSM 'maxspeed' tag is explicitly present and non-empty."""
    if raw_tag is None or raw_tag is False:
        return False
    if isinstance(raw_tag, (int, float)):
        return math.isfinite(float(raw_tag)) and float(raw_tag) > 0
    if isinstance(raw_tag, (list, tuple, set)):
        return any(_has_observed_maxspeed(x) for x in raw_tag)
    val = str(raw_tag).strip().lower()
    return val not in ("", "none", "nan", "null")


def compute_road_hierarchy_quality_unit(highway_class: str) -> float:
    """
    Map a highway class to a [0, 1] quality weight derived linearly from its
    established design speed in MOUNTAIN_HIGHWAY_SPEEDS_KPH ([15.0, 45.0] km/h).
    """
    design_speed = MOUNTAIN_HIGHWAY_SPEEDS_KPH.get(highway_class, FALLBACK_SPEED_KPH)
    span = MAX_DESIGN_SPEED_KPH - MIN_DESIGN_SPEED_KPH
    if span <= 0:
        return 0.5
    unit = (design_speed - MIN_DESIGN_SPEED_KPH) / span
    return max(0.0, min(1.0, unit))


def summarize_edge_attributes(edge_records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute verifiable edge-level composition and completeness metrics from a list of
    traversed edge dictionaries along a candidate path.
    """
    if not edge_records:
        return {
            "total_edges": 0,
            "road_hierarchy_score": 100.0,
            "road_class_breakdown_pct": {
                "major_arterial": 0.0,
                "secondary_collector": 0.0,
                "local_unclassified": 0.0,
            },
            "highway_length_m_by_class": {},
            "imputed_speed_edges_pct": 0.0,
            "imputed_highway_edges_count": 0,
            "bridges_count": 0,
            "tunnels_count": 0,
            "bridge_tunnel_edges_pct": 0.0,
        }

    total_length_m = 0.0
    weighted_hierarchy_sum = 0.0
    major_length_m = 0.0
    secondary_length_m = 0.0
    local_length_m = 0.0
    class_lengths: dict[str, float] = {}

    imputed_speed_edges = 0
    imputed_highway_edges = 0
    bridges_count = 0
    tunnels_count = 0

    for edge in edge_records:
        raw_len = edge.get("length", 0.0)
        try:
            length_m = max(0.0, float(raw_len)) if raw_len is not None else 0.0
        except (TypeError, ValueError):
            length_m = 0.0
        if not math.isfinite(length_m):
            length_m = 0.0

        hwy_class, was_hwy_imputed = normalize_highway_tag(edge.get("highway"))
        if was_hwy_imputed:
            imputed_highway_edges += 1

        if not _has_observed_maxspeed(edge.get("maxspeed")):
            imputed_speed_edges += 1

        if _is_truthy_structure_tag(edge.get("bridge")):
            bridges_count += 1
        if _is_truthy_structure_tag(edge.get("tunnel")):
            tunnels_count += 1

        q_unit = compute_road_hierarchy_quality_unit(hwy_class)
        total_length_m += length_m
        weighted_hierarchy_sum += length_m * q_unit
        class_lengths[hwy_class] = round(class_lengths.get(hwy_class, 0.0) + length_m, 2)

        if hwy_class in MAJOR_ARTERIAL_CLASSES:
            major_length_m += length_m
        elif hwy_class in SECONDARY_COLLECTOR_CLASSES:
            secondary_length_m += length_m
        else:
            local_length_m += length_m

    total_edges = len(edge_records)
    if total_length_m > 0:
        hierarchy_score = _round1(_clamp(100.0 * (weighted_hierarchy_sum / total_length_m)))
        major_pct = _round1(100.0 * major_length_m / total_length_m)
        secondary_pct = _round1(100.0 * secondary_length_m / total_length_m)
        local_pct = _round1(max(0.0, 100.0 - major_pct - secondary_pct))
    else:
        hierarchy_score = 100.0
        major_pct = 0.0
        secondary_pct = 0.0
        local_pct = 0.0

    imputed_speed_pct = _round1(100.0 * imputed_speed_edges / total_edges)
    bridge_tunnel_pct = _round1(
        100.0 * min(total_edges, bridges_count + tunnels_count) / total_edges
    )

    return {
        "total_edges": total_edges,
        "road_hierarchy_score": hierarchy_score,
        "road_class_breakdown_pct": {
            "major_arterial": major_pct,
            "secondary_collector": secondary_pct,
            "local_unclassified": local_pct,
        },
        "highway_length_m_by_class": class_lengths,
        "imputed_speed_edges_pct": imputed_speed_pct,
        "imputed_highway_edges_count": imputed_highway_edges,
        "bridges_count": bridges_count,
        "tunnels_count": tunnels_count,
        "bridge_tunnel_edges_pct": bridge_tunnel_pct,
    }


def compute_snap_quality_score(
    origin_snap_m: float,
    destination_snap_m: float,
    max_snap_distance_m: float = 3000.0,
) -> float:
    """
    Compute endpoint snapping quality score on [0, 100]:
      S_snap = 100 * (1 - (d_orig + d_dest) / (2 * d_max))
    """
    if max_snap_distance_m <= 0:
        return 100.0
    d_orig = max(0.0, float(origin_snap_m)) if math.isfinite(float(origin_snap_m)) else max_snap_distance_m
    d_dest = max(0.0, float(destination_snap_m)) if math.isfinite(float(destination_snap_m)) else max_snap_distance_m
    ratio = (d_orig + d_dest) / (2.0 * float(max_snap_distance_m))
    return _round1(_clamp(100.0 * (1.0 - ratio)))


def check_candidates_identical(candidates: list[dict[str, Any]]) -> bool:
    """Return True if all candidate routes represent the exact same path or metrics."""
    if len(candidates) <= 1:
        return True
    first = candidates[0]
    first_nodes = first.get("node_ids") or []
    first_dist = float(first.get("distance_km", 0.0))
    first_time = float(first.get("estimated_duration_min", 0.0))

    for other in candidates[1:]:
        other_nodes = other.get("node_ids") or []
        other_dist = float(other.get("distance_km", 0.0))
        other_time = float(other.get("estimated_duration_min", 0.0))
        if first_nodes and other_nodes and first_nodes == other_nodes:
            continue
        if abs(first_dist - other_dist) < 1e-3 and abs(first_time - other_time) < 0.05:
            continue
        return False
    return True


def evaluate_candidate_routes(
    candidates: list[dict[str, Any]],
    preference: RoutePreferenceType = "balanced",
    origin_snap_m: float = 0.0,
    destination_snap_m: float = 0.0,
    max_snap_distance_m: float = 3000.0,
    weather_evaluations: dict[str, dict[str, Any]] | None = None,
    disruption_evaluations: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Deterministically score, compare, and rank candidate routes using measurable
    evidence extracted from the road graph, live atmospheric forecasts, and verified road advisories.

    Handles edge cases:
    - Empty candidate list
    - Single candidate route
    - Zero-distance route (origin_node == destination_node)
    - Identical candidate routes (shortest and fastest converge on the same path)
    - Missing edge attributes
    """
    pref_key: RoutePreferenceType = (
        preference if preference in PREFERENCE_WEIGHTS else "balanced"
    )
    weight_cfg = PREFERENCE_WEIGHTS[pref_key]
    w_dist = float(weight_cfg["distance"])
    w_time = float(weight_cfg["time"])
    w_hier = float(weight_cfg["road_hierarchy"])

    snap_score = compute_snap_quality_score(
        origin_snap_m=origin_snap_m,
        destination_snap_m=destination_snap_m,
        max_snap_distance_m=max_snap_distance_m,
    )

    if not candidates:
        return {
            "preference": pref_key,
            "scoring_method": "deterministic_multi_criteria_v1",
            "weights": {
                "distance": w_dist,
                "time": w_time,
                "road_hierarchy": w_hier,
            },
            "formula": weight_cfg["formula"],
            "recommended_route_id": None,
            "routes_are_identical": True,
            "snap_coverage_score": snap_score,
            "recommendation_rationale": "No candidate routes available to evaluate.",
            "candidates": [],
            "limitations_and_unavailable_criteria": list(
                DEFAULT_LIMITATIONS_AND_UNAVAILABLE_CRITERIA
            ),
        }

    positive_distances = [
        float(c.get("distance_km", 0.0))
        for c in candidates
        if math.isfinite(float(c.get("distance_km", 0.0))) and float(c.get("distance_km", 0.0)) > 0
    ]
    positive_durations = [
        float(c.get("estimated_duration_min", 0.0))
        for c in candidates
        if math.isfinite(float(c.get("estimated_duration_min", 0.0)))
        and float(c.get("estimated_duration_min", 0.0)) > 0
    ]

    min_distance_km = min(positive_distances) if positive_distances else 0.0
    min_duration_min = min(positive_durations) if positive_durations else 0.0
    routes_are_identical = check_candidates_identical(candidates)

    scored_entries: list[dict[str, Any]] = []
    for cand in candidates:
        route_id = str(cand.get("route_type") or cand.get("route_id") or "candidate")
        route_type = str(cand.get("route_type") or route_id)
        dist_km = max(0.0, float(cand.get("distance_km", 0.0)))
        dur_min = max(0.0, float(cand.get("estimated_duration_min", 0.0)))
        num_nodes = int(cand.get("num_nodes", len(cand.get("node_ids", []))))

        # 1. Distance efficiency score (0-100)
        if dist_km <= 0.0 or min_distance_km <= 0.0:
            dist_score = 100.0
        else:
            dist_score = _round1(_clamp(100.0 * (min_distance_km / dist_km)))

        # 2. Estimated time efficiency score (0-100)
        if dur_min <= 0.0 or min_duration_min <= 0.0:
            time_score = 100.0
        else:
            time_score = _round1(_clamp(100.0 * (min_duration_min / dur_min)))

        # 3. Road-class hierarchy score (0-100)
        edge_summary = cand.get("edge_summary")
        if not isinstance(edge_summary, dict):
            edge_summary = summarize_edge_attributes(cand.get("edge_records", []))
        hierarchy_score = float(edge_summary.get("road_hierarchy_score", 100.0 if dist_km == 0 else 50.0))

        # 4. Overall deterministic score
        overall_score = _round1(
            _clamp(w_dist * dist_score + w_time * time_score + w_hier * hierarchy_score)
        )

        implied_speed_kph = (
            _round1(dist_km / (dur_min / 60.0)) if dur_min > 0 else 0.0
        )
        intersection_density = (
            _round2(num_nodes / dist_km) if dist_km > 0 else 0.0
        )

        # Weather exposure evaluation
        route_weather = (weather_evaluations or {}).get(route_id) or (weather_evaluations or {}).get(route_type)
        weather_score = (
            route_weather.get("weather_exposure_score")
            if isinstance(route_weather, dict)
            else None
        )

        # Disruptions evaluation
        route_disruptions = (disruption_evaluations or {}).get(route_id) or (disruption_evaluations or {}).get(route_type)
        disruption_score = (
            route_disruptions.get("confirmed_disruptions_score")
            if isinstance(route_disruptions, dict)
            else None
        )

        comp_scores: dict[str, Any] = {
            "distance_score": dist_score,
            "time_score": time_score,
            "road_hierarchy_score": hierarchy_score,
            "snap_quality_score": snap_score,
            "completeness_score": _round1(
                _clamp(
                    100.0
                    - (
                        100.0
                        * float(edge_summary.get("imputed_highway_edges_count", 0))
                        / max(1, int(edge_summary.get("total_edges", 1)))
                    )
                )
            ),
        }
        if weather_score is not None:
            comp_scores["weather_exposure_score"] = weather_score
        if disruption_score is not None:
            comp_scores["confirmed_disruptions_score"] = disruption_score

        unavail_scores: dict[str, Any] = {
            "live_traffic_score": None,
        }
        if weather_score is None:
            unavail_scores["weather_exposure_score"] = None
        if disruption_score is None:
            unavail_scores["confirmed_disruptions_score"] = None

        cand_advantages: list[str] = []
        cand_disadvantages: list[str] = []

        if route_disruptions and isinstance(route_disruptions, dict):
            intersected = route_disruptions.get("intersected_disruptions", [])
            if not intersected and route_disruptions.get("status") == "clear":
                cand_advantages.append(
                    "Corridor is 100% clear of all active regional road maintenance advisories."
                )
            for d_item in intersected:
                cand_disadvantages.append(
                    f"Intersects {d_item.get('title')} ({d_item.get('severity', '').upper()}): {d_item.get('description')}"
                )

        if route_weather and isinstance(route_weather, dict):
            haz = route_weather.get("hazard_level")
            guidance = route_weather.get("guidance", "")
            if haz == "low":
                cand_advantages.append(f"Corridor weather: {guidance}")
            elif haz == "high":
                cand_disadvantages.append(f"Adverse weather condition: {guidance}")

        scored_entries.append(
            {
                "route_id": route_id,
                "route_type": route_type,
                "rank": 1,
                "overall_score": overall_score,
                "component_scores": comp_scores,
                "unavailable_component_scores": unavail_scores,
                "evidence": {
                    "distance_km": _round2(dist_km),
                    "estimated_duration_min": _round1(dur_min),
                    "distance_delta_from_best_km": _round2(max(0.0, dist_km - min_distance_km)),
                    "duration_delta_from_best_min": _round1(max(0.0, dur_min - min_duration_min)),
                    "implied_avg_speed_kph": implied_speed_kph,
                    "num_nodes": num_nodes,
                    "intersection_density_per_km": intersection_density,
                    "road_class_breakdown_pct": edge_summary.get(
                        "road_class_breakdown_pct",
                        {
                            "major_arterial": 0.0,
                            "secondary_collector": 0.0,
                            "local_unclassified": 0.0,
                        },
                    ),
                    "imputed_speed_edges_pct": float(
                        edge_summary.get("imputed_speed_edges_pct", 100.0)
                    ),
                    "bridges_count": int(edge_summary.get("bridges_count", 0)),
                    "tunnels_count": int(edge_summary.get("tunnels_count", 0)),
                },
                "advantages": cand_advantages,
                "disadvantages": cand_disadvantages,
            }
        )

    # Sort deterministically with explicit tie-breaking rules
    def _sort_key(item: dict[str, Any]) -> tuple[float, int, float, float]:
        score = float(item["overall_score"])
        ev = item["evidence"]
        r_type = item["route_type"]
        if pref_key == "shortest":
            pref_type_bonus = 1 if r_type == "shortest" else 0
            return (-score, -pref_type_bonus, float(ev["distance_km"]), float(ev["estimated_duration_min"]))
        if pref_key == "fastest":
            pref_type_bonus = 1 if r_type == "estimated_fastest" else 0
            return (-score, -pref_type_bonus, float(ev["estimated_duration_min"]), float(ev["distance_km"]))
        pref_type_bonus = 1 if r_type == "estimated_fastest" else 0
        return (-score, -pref_type_bonus, float(ev["estimated_duration_min"]), float(ev["distance_km"]))

    scored_entries.sort(key=_sort_key)

    for idx, entry in enumerate(scored_entries):
        entry["rank"] = idx + 1

    # Populate comparative advantages and disadvantages
    for entry in scored_entries:
        ev = entry["evidence"]
        comp = entry["component_scores"]
        others = [o for o in scored_entries if o["route_id"] != entry["route_id"]]

        if ev["distance_km"] == 0.0:
            entry["advantages"].append(
                "Origin and destination snap to the same road node (0.0 km traversal)."
            )
            continue

        if routes_are_identical or not others:
            entry["advantages"].append(
                f"Single dominant corridor ({ev['distance_km']} km, {ev['estimated_duration_min']} min est.) optimal for both distance and time."
            )
            continue

        ref = others[0]
        ref_ev = ref["evidence"]
        dist_diff = _round2(ev["distance_km"] - ref_ev["distance_km"])
        time_diff = _round1(ev["estimated_duration_min"] - ref_ev["estimated_duration_min"])
        arterial_pct = ev["road_class_breakdown_pct"]["major_arterial"]
        ref_arterial_pct = ref_ev["road_class_breakdown_pct"]["major_arterial"]

        if dist_diff < -0.01:
            entry["advantages"].append(
                f"Saves {abs(dist_diff):.2f} km physical distance compared with {ref['route_type']} ({ev['distance_km']} km vs. {ref_ev['distance_km']} km; S_dist={comp['distance_score']}/100)."
            )
        elif dist_diff > 0.01:
            entry["disadvantages"].append(
                f"Adds +{dist_diff:.2f} km extra distance compared with {ref['route_type']} ({ev['distance_km']} km vs. {ref_ev['distance_km']} km; S_dist={comp['distance_score']}/100)."
            )

        if time_diff < -0.05:
            entry["advantages"].append(
                f"Reduces static estimated travel time by {abs(time_diff):.1f} min compared with {ref['route_type']} ({ev['estimated_duration_min']} min vs. {ref_ev['estimated_duration_min']} min; S_time={comp['time_score']}/100)."
            )
        elif time_diff > 0.05:
            entry["disadvantages"].append(
                f"Requires +{time_diff:.1f} min longer estimated travel time than {ref['route_type']} ({ev['estimated_duration_min']} min vs. {ref_ev['estimated_duration_min']} min; S_time={comp['time_score']}/100)."
            )

        if arterial_pct > ref_arterial_pct + 1.0:
            entry["advantages"].append(
                f"Higher major arterial road share ({arterial_pct}% trunk/primary vs. {ref_arterial_pct}% on {ref['route_type']}; S_hierarchy={comp['road_hierarchy_score']}/100)."
            )
        elif arterial_pct + 1.0 < ref_arterial_pct:
            entry["disadvantages"].append(
                f"Lower major arterial road share ({arterial_pct}% trunk/primary vs. {ref_arterial_pct}% on {ref['route_type']}; S_hierarchy={comp['road_hierarchy_score']}/100)."
            )

        if not entry["advantages"]:
            entry["advantages"].append(
                f"Achieves overall score {entry['overall_score']}/100 across {ev['num_nodes']} road nodes."
            )
        if not entry["disadvantages"]:
            entry["disadvantages"].append(
                "Relies on static highway-class speed imputation rather than live traffic telemetry."
            )

    top = scored_entries[0]
    top_ev = top["evidence"]
    if top_ev["distance_km"] == 0.0:
        rationale = (
            "Origin and destination resolve to the same road network node "
            f"(0.0 km, 0.0 min; score {top['overall_score']}/100)."
        )
    elif routes_are_identical or len(scored_entries) == 1:
        rationale = (
            f"Shortest-distance and fastest-estimated searches converge on the exact same "
            f"{top_ev['num_nodes']}-node road corridor ({top_ev['distance_km']} km, "
            f"{top_ev['estimated_duration_min']} min est.), achieving {top['overall_score']}/100 "
            f"under {weight_cfg['label']}."
        )
    else:
        runner_up = scored_entries[1]
        rationale = (
            f"Under {weight_cfg['label']} ({weight_cfg['formula']}), "
            f"'{top['route_type']}' ranks #1 with {top['overall_score']}/100 "
            f"(vs. {runner_up['overall_score']}/100 for '{runner_up['route_type']}'). "
            f"{top['advantages'][0]}"
        )

    return {
        "preference": pref_key,
        "scoring_method": "deterministic_multi_criteria_v1",
        "weights": {
            "distance": w_dist,
            "time": w_time,
            "road_hierarchy": w_hier,
        },
        "formula": weight_cfg["formula"],
        "recommended_route_id": top["route_id"],
        "routes_are_identical": routes_are_identical,
        "snap_coverage_score": snap_score,
        "recommendation_rationale": rationale,
        "candidates": scored_entries,
        "limitations_and_unavailable_criteria": list(
            DEFAULT_LIMITATIONS_AND_UNAVAILABLE_CRITERIA
        ),
    }

