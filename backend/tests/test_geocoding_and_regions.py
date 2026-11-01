from __future__ import annotations

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
for _p in [_ROOT, _ROOT / 'core', _ROOT / 'services']:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


import json

from geocoding_service import (
    EmptyGeocodeQueryError,
    GeocodingService,
    InvalidCoordinateQueryError,
)
from region_manager import RegionGraphManager
from route_engine import RouteEngine


def main() -> None:
    print("=" * 72)
    print("TESTING GEOCODING SERVICE & MULTI-REGION GRAPH MANAGER (STAGE 2)")
    print("=" * 72)

    engine = RouteEngine()
    region_mgr = RegionGraphManager()
    region_mgr.register_engine_instance(region_mgr.default_region_id, engine)
    geocoder = GeocodingService(
        region_manager=region_mgr,
        allow_external_nominatim=False,  # Test deterministic offline mode in sandbox
    )

    # 1. Test regional catalog status listing across all 8 NER states
    print("\n[1] Verifying Regional Road-Graph Catalog (All 8 North Eastern States)")
    regions = region_mgr.list_regions_status()
    assert len(regions) == 10, f"Expected 10 catalog regions, got {len(regions)}"
    covered_states = {r["state"] for r in regions}
    for required_state in (
        "Meghalaya",
        "Assam",
        "Arunachal Pradesh",
        "Manipur",
        "Mizoram",
        "Nagaland",
        "Tripura",
        "Sikkim",
    ):
        assert required_state in covered_states, f"Missing NER state {required_state} in catalog"
    shillong_reg = next(r for r in regions if r["region_id"] == "meghalaya_shillong_sohra")
    assert shillong_reg["installed_on_disk"] is True
    assert shillong_reg["loaded_in_memory"] is True
    assert shillong_reg["nodes"] == 21764
    print(
        f"    Catalog contains {len(regions)} regions across all 8 NER states; "
        f"default '{shillong_reg['region_id']}' installed & loaded."
    )

    # 2. Test in-coverage place search (Shillong & Sohra/Cherrapunji)
    print("\n[2] Testing text search for in-coverage locations ('Shillong, Meghalaya' & 'Cherrapunji')")
    shillong_res = geocoder.search_places("Shillong, Meghalaya", active_engine=engine)
    assert shillong_res["count"] >= 1
    top_shillong = shillong_res["results"][0]
    assert top_shillong["place_id"] == "shillong"
    assert top_shillong["coverage"]["within_loaded_graph"] is True
    assert top_shillong["coverage"]["status"] == "routable_in_loaded_graph"
    assert top_shillong["coverage"]["snap_distance_m"] < 50.0

    sohra_res = geocoder.search_places("Cherrapunji", active_engine=engine)
    assert sohra_res["count"] >= 1
    top_sohra = sohra_res["results"][0]
    assert top_sohra["place_id"] == "sohra"
    assert top_sohra["coverage"]["within_loaded_graph"] is True
    print(
        f"    Resolved 'Shillong, Meghalaya' -> ({top_shillong['lat']}, {top_shillong['lng']}), "
        f"snap={top_shillong['coverage']['snap_distance_m']} m ({top_shillong['coverage']['status']})"
    )
    print(
        f"    Resolved 'Cherrapunji' -> ({top_sohra['lat']}, {top_sohra['lng']}), "
        f"snap={top_sohra['coverage']['snap_distance_m']} m ({top_sohra['coverage']['status']})"
    )

    # 3. Test expandable catalog region locations across all other NER states
    print("\n[3] Testing text search for expandable catalog regions across NER states")
    ner_expandable_queries = [
        ("Guwahati, Assam", "guwahati", "assam_guwahati_nongpoh"),
        ("Jowai", "jowai", "meghalaya_jaintia_jowai"),
        ("Itanagar", "itanagar_arunachal", "arunachal_itanagar_naharlagun"),
        ("Imphal", "imphal_manipur", "manipur_imphal_valley"),
        ("Aizawl", "aizawl_mizoram", "mizoram_aizawl_corridor"),
        ("Kohima", "kohima_nagaland", "nagaland_kohima_dimapur"),
        ("Agartala", "agartala_tripura", "tripura_agartala_corridor"),
        ("Gangtok, Sikkim", "gangtok_sikkim", "sikkim_gangtok_nh10"),
    ]
    for q_text, expected_pid, expected_reg_id in ner_expandable_queries:
        res = geocoder.search_places(q_text, active_engine=engine)
        assert res["count"] >= 1, f"No results for {q_text}"
        top_hit = res["results"][0]
        assert top_hit["place_id"] == expected_pid, f"Expected {expected_pid}, got {top_hit['place_id']}"
        assert top_hit["coverage"]["within_loaded_graph"] is False
        assert top_hit["coverage"]["status"] == "supported_region_not_downloaded"
        assert top_hit["coverage"]["region_id"] == expected_reg_id
        assert top_hit["coverage"]["acquire_command"] == f"python backend/region_manager.py --acquire {expected_reg_id}"
        print(
            f"    Resolved '{q_text}' -> region={expected_reg_id}, "
            f"status={top_hit['coverage']['status']}"
        )

    # 4. Test out-of-all-regions location ('New Delhi')
    print("\n[4] Testing text search for distant location outside catalog ('New Delhi')")
    delhi_res = geocoder.search_places("New Delhi", active_engine=engine)
    assert delhi_res["count"] >= 1
    top_delhi = delhi_res["results"][0]
    assert top_delhi["coverage"]["within_loaded_graph"] is False
    assert top_delhi["coverage"]["status"] == "outside_all_catalog_regions"
    print(f"    Resolved 'New Delhi' -> status={top_delhi['coverage']['status']}")

    # 5. Test direct coordinate string parsing
    print("\n[5] Testing direct 'lat, lng' coordinate string lookup")
    coord_res = geocoder.search_places("25.5653, 91.6375", active_engine=engine)
    assert coord_res["count"] == 1
    assert coord_res["geocoder_source"] == "direct_coordinate_parser"
    assert coord_res["results"][0]["coverage"]["within_loaded_graph"] is True
    print(
        f"    Parsed '25.5653, 91.6375' -> snap={coord_res['results'][0]['coverage']['snap_distance_m']} m"
    )

    # 6. Test empty and invalid coordinate error handling
    print("\n[6] Testing empty query and invalid coordinate query error handling")
    try:
        geocoder.search_places("   ", active_engine=engine)
        raise AssertionError("Expected EmptyGeocodeQueryError")
    except EmptyGeocodeQueryError as err:
        print(f"    Correctly rejected empty query: {err}")

    try:
        geocoder.search_places("105.5, 91.8", active_engine=engine)
        raise AssertionError("Expected InvalidCoordinateQueryError")
    except InvalidCoordinateQueryError as err:
        print(f"    Correctly rejected out-of-range coordinate string: {err}")

    print("\n" + "=" * 72)
    print("ALL GEOCODING & MULTI-REGION MANAGER TESTS PASSED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()

