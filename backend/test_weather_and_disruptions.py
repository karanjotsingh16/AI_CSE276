from __future__ import annotations

import json
from pathlib import Path

from disruptions_service import DisruptionsService
from route_engine import RouteEngine
from weather_service import WeatherService

BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    print("=" * 72)
    print("TESTING WEATHER INTELLIGENCE & DISRUPTIONS INTEGRATION (PHASE 3)")
    print("=" * 72)

    # 1. Test DisruptionsService
    print("\n[1] Testing DisruptionsService catalog and active advisories")
    disrupt_svc = DisruptionsService()
    active = disrupt_svc.list_active_disruptions()
    assert len(active) >= 4, f"Expected at least 4 regional advisories, got {len(active)}"
    print(f"    Loaded {len(active)} active verified regional road disruption advisories:")
    for d in active:
        print(f"      • [{d['severity'].upper()}] {d['title']} ({d['issuing_agency']})")
        assert "latitude" in d and "longitude" in d and "radius_m" in d
        assert d["data_source"] == "official_regional_advisory"

    # 2. Test Disruption Spatial Intersections
    print("\n[2] Testing spatial corridor intersection logic")
    # Coordinates passing directly through Mawkdok Valley advisory (lat 25.3520, lng 91.7580)
    corridor_passing_mawkdok = [
        [91.8933, 25.5788],  # Shillong
        [91.7580, 25.3520],  # Mawkdok escarpment
        [91.7323, 25.2750],  # Sohra
    ]
    eval_mawkdok = disrupt_svc.evaluate_route_disruptions(corridor_passing_mawkdok)
    assert eval_mawkdok["intersected_count"] >= 1
    assert any(i["id"] == "disruption_sohra_mawkdok_culvert_2026_03" for i in eval_mawkdok["intersected_disruptions"])
    assert eval_mawkdok["confirmed_disruptions_score"] < 100.0
    print(f"    Correctly detected advisory intersection: score={eval_mawkdok['confirmed_disruptions_score']}/100, intersected={eval_mawkdok['intersected_count']}")

    # Coordinates in west Meghalaya (Mairang area) far away from Sonapur Ghat (East Jaintia)
    corridor_clear = [
        [91.6426, 25.5593],
        [91.6400, 25.5600],
    ]
    eval_clear = disrupt_svc.evaluate_route_disruptions(corridor_clear)
    assert eval_clear["intersected_count"] == 0
    assert eval_clear["confirmed_disruptions_score"] == 100.0
    assert eval_clear["status"] == "clear"
    print("    Correctly verified clear corridor: score=100.0/100, zero intersections.")

    # 3. Test WeatherService
    print("\n[3] Testing WeatherService point fetch and caching")
    weather_svc = WeatherService()
    shillong_weather = weather_svc.fetch_point_weather(25.5788, 91.8933, location_name="Shillong Hub")
    assert shillong_weather["status"] in ("available", "unavailable")
    print(f"    Shillong weather status: {shillong_weather['status']}")
    if shillong_weather["status"] == "available":
        print(f"      Temperature: {shillong_weather['temperature_c']} °C")
        print(f"      Wind speed: {shillong_weather['wind_speed_kmh']} km/h")
        print(f"      Rain probability: {shillong_weather['max_rain_probability_pct']} %")
        assert len(shillong_weather["hourly_forecast"]) > 0

    # Test cache hit on second fetch
    shillong_cached = weather_svc.fetch_point_weather(25.5788, 91.8933)
    assert shillong_cached.get("from_cache") is True
    print("    Verified memory/disk cache hit on repeated coordinate query.")

    # 4. Test Route Corridor Weather Evaluation
    print("\n[4] Testing route corridor weather evaluation")
    shillong_sohra_corridor = [
        [91.8933, 25.5788],
        [91.8300, 25.4300],
        [91.7323, 25.2750],
    ]
    corridor_w = weather_svc.evaluate_route_corridor_weather(shillong_sohra_corridor)
    print(f"    Corridor weather status: {corridor_w['corridor_status']}")
    if corridor_w["corridor_status"] == "available":
        assert 0.0 <= corridor_w["weather_exposure_score"] <= 100.0
        print(f"    Corridor weather score: {corridor_w['weather_exposure_score']}/100 (hazard: {corridor_w['hazard_level']})")
        print(f"    Guidance: {corridor_w['guidance']}")

    # 5. Test Live RouteEngine End-to-End Integration
    print("\n[5] Testing RouteEngine live calculation with weather & disruptions enrichment")
    engine = RouteEngine()
    result = engine.calculate_routes(
        origin_lat=25.5788,
        origin_lng=91.8933,
        destination_lat=25.2750,
        destination_lng=91.7323,
        preference="accessibility",
    )
    assert "routes" in result
    assert "evaluation" in result
    assert "weather_summary" in result
    assert "disruptions_summary" in result

    fastest = result["routes"]["estimated_fastest"]
    assert "weather" in fastest
    assert "disruptions" in fastest

    eval_cands = result["evaluation"]["candidates"]
    top_cand = eval_cands[0]
    comp = top_cand["component_scores"]
    print("    Top candidate component scores:")
    for k, v in comp.items():
        print(f"      • {k}: {v}")

    # Verify weather and disruptions scores are present in component_scores (or unavail if offline)
    assert "distance_score" in comp
    assert "time_score" in comp
    assert "road_hierarchy_score" in comp
    assert "confirmed_disruptions_score" in comp
    # Verify live traffic remains strictly unavailable
    assert result["evaluation"]["candidates"][0]["unavailable_component_scores"]["live_traffic_score"] is None

    print("\n" + "=" * 72)
    print("ALL WEATHER & DISRUPTIONS TESTS PASSED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()
