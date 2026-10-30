from __future__ import annotations

import json
import math

from route_engine import RouteEngine
from route_scoring import (
    compute_road_hierarchy_quality_unit,
    compute_snap_quality_score,
    evaluate_candidate_routes,
    normalize_highway_tag,
    summarize_edge_attributes,
)


def main() -> None:
    print("=" * 72)
    print("TESTING EXPLAINABLE ROUTE EVALUATION & SCORING (STAGE 1)")
    print("=" * 72)

    # 1. Test highway tag normalization & missingness handling
    print("\n[1] Testing highway tag normalization and list/missing edge cases")
    assert normalize_highway_tag("primary") == ("primary", False)
    assert normalize_highway_tag(["residential", "trunk"]) == ("trunk", False)
    assert normalize_highway_tag("['secondary', 'tertiary']") == ("secondary", False)
    assert normalize_highway_tag(None) == ("unclassified", True)
    assert normalize_highway_tag("") == ("unclassified", True)
    assert math.isclose(compute_road_hierarchy_quality_unit("trunk"), 1.0, abs_tol=1e-4)
    assert math.isclose(compute_road_hierarchy_quality_unit("living_street"), 0.0, abs_tol=1e-4)
    print("    Highway tag normalization and [0, 1] design-speed scaling verified.")

    # 2. Test edge attribute summary calculation
    print("\n[2] Testing edge attribute summary (road-class composition, bridges, maxspeed)")
    sample_edges = [
        {"length": 600.0, "highway": "trunk", "maxspeed": "40", "bridge": "yes"},
        {"length": 300.0, "highway": "secondary", "maxspeed": None, "bridge": None},
        {"length": 100.0, "highway": None, "maxspeed": None, "tunnel": "yes"},
    ]
    edge_sum = summarize_edge_attributes(sample_edges)
    assert edge_sum["total_edges"] == 3
    assert math.isclose(edge_sum["road_class_breakdown_pct"]["major_arterial"], 60.0, abs_tol=0.1)
    assert math.isclose(edge_sum["road_class_breakdown_pct"]["secondary_collector"], 30.0, abs_tol=0.1)
    assert math.isclose(edge_sum["road_class_breakdown_pct"]["local_unclassified"], 10.0, abs_tol=0.1)
    assert edge_sum["bridges_count"] == 1
    assert edge_sum["tunnels_count"] == 1
    assert edge_sum["imputed_highway_edges_count"] == 1
    assert math.isclose(edge_sum["imputed_speed_edges_pct"], 66.7, abs_tol=0.2)
    print(f"    Edge summary verified: {json.dumps(edge_sum)}")

    # 3. Test snapping quality formula
    print("\n[3] Testing endpoint snapping quality formula")
    assert compute_snap_quality_score(0.0, 0.0, 3000.0) == 100.0
    assert compute_snap_quality_score(3000.0, 3000.0, 3000.0) == 0.0
    assert compute_snap_quality_score(1500.0, 1500.0, 3000.0) == 50.0
    print("    Snap quality score bounds [0, 100] verified.")

    # 4. Test edge cases: zero-distance route, identical candidates, single route
    print("\n[4] Testing edge cases (zero-distance, identical candidates, single route)")
    zero_route = [
        {
            "route_type": "shortest",
            "node_ids": [101],
            "num_nodes": 1,
            "distance_km": 0.0,
            "estimated_duration_min": 0.0,
            "edge_records": [],
        }
    ]
    zero_eval = evaluate_candidate_routes(zero_route, preference="balanced")
    assert zero_eval["recommended_route_id"] == "shortest"
    assert zero_eval["candidates"][0]["overall_score"] == 100.0
    assert "same road network node" in zero_eval["recommendation_rationale"]

    identical_routes = [
        {
            "route_type": "shortest",
            "node_ids": [1, 2, 3],
            "num_nodes": 3,
            "distance_km": 15.0,
            "estimated_duration_min": 25.0,
            "edge_summary": {"road_hierarchy_score": 80.0, "road_class_breakdown_pct": {"major_arterial": 70.0, "secondary_collector": 20.0, "local_unclassified": 10.0}},
        },
        {
            "route_type": "estimated_fastest",
            "node_ids": [1, 2, 3],
            "num_nodes": 3,
            "distance_km": 15.0,
            "estimated_duration_min": 25.0,
            "edge_summary": {"road_hierarchy_score": 80.0, "road_class_breakdown_pct": {"major_arterial": 70.0, "secondary_collector": 20.0, "local_unclassified": 10.0}},
        },
    ]
    ident_eval = evaluate_candidate_routes(identical_routes, preference="balanced")
    assert ident_eval["routes_are_identical"] is True
    assert ident_eval["candidates"][0]["overall_score"] == ident_eval["candidates"][1]["overall_score"]
    print("    Zero-distance and identical-candidate edge cases passed.")

    # 5. Test live RouteEngine Shillong -> Sohra across all 4 preference modes + 3rd distinct alternative
    print("\n[5] Testing live RouteEngine evaluation on Shillong -> Sohra across all 4 preferences")
    engine = RouteEngine()
    res_shortest = engine.calculate_routes(25.5788, 91.8933, 25.2750, 91.7323, preference="shortest")
    res_fastest = engine.calculate_routes(25.5788, 91.8933, 25.2750, 91.7323, preference="fastest")
    res_balanced = engine.calculate_routes(25.5788, 91.8933, 25.2750, 91.7323, preference="balanced")
    res_access = engine.calculate_routes(25.5788, 91.8933, 25.2750, 91.7323, preference="accessibility")

    assert res_shortest["evaluation"]["recommended_route_id"] == "shortest"
    assert res_shortest["evaluation"]["candidates"][0]["overall_score"] == 100.0

    assert res_fastest["evaluation"]["recommended_route_id"] == "estimated_fastest"
    assert res_fastest["evaluation"]["candidates"][0]["overall_score"] == 100.0

    assert res_balanced["evaluation"]["recommended_route_id"] == "estimated_fastest"
    assert res_access["evaluation"]["recommended_route_id"] == "estimated_fastest"

    # Verify 3 distinct deduplicated alternatives exist on Shillong -> Sohra
    assert len(res_balanced["alternatives"]) == 3
    alt_types = [r["route_type"] for r in res_balanced["alternatives"]]
    assert alt_types == ["estimated_fastest", "shortest", "alternative_corridor"]

    # Verify deduplication collapses identical paths into 1 unique alternative
    deduped_ident = RouteEngine.deduplicate_candidate_routes(identical_routes)
    assert len(deduped_ident) == 1
    assert deduped_ident[0]["merged_route_types"] == ["shortest", "estimated_fastest"]

    bal_top = res_balanced["evaluation"]["candidates"][0]
    bal_second = res_balanced["evaluation"]["candidates"][1]
    assert bal_top["overall_score"] > bal_second["overall_score"]
    assert bal_top["component_scores"]["time_score"] == 100.0
    assert bal_second["component_scores"]["distance_score"] == 100.0
    assert bal_top["unavailable_component_scores"]["weather_exposure_score"] is None
    assert bal_top["unavailable_component_scores"]["confirmed_disruptions_score"] is None
    assert bal_top["unavailable_component_scores"]["live_traffic_score"] is None

    print(
        json.dumps(
            {
                "balanced_recommended": bal_top["route_id"],
                "balanced_top_score": bal_top["overall_score"],
                "balanced_top_components": bal_top["component_scores"],
                "balanced_top_road_classes_pct": bal_top["evidence"]["road_class_breakdown_pct"],
                "balanced_runner_up_score": bal_second["overall_score"],
                "rationale": res_balanced["evaluation"]["recommendation_rationale"],
            },
            indent=2,
        )
    )

    print("\n" + "=" * 72)
    print("ALL ROUTE SCORING & EVALUATION TESTS PASSED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()

