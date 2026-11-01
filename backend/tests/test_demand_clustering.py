from __future__ import annotations

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
for _p in [_ROOT, _ROOT / 'core', _ROOT / 'services']:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


import json
import math

from demand_clustering import (
    DEFAULT_EVALUATION_REPORT_PATH,
    DEFAULT_SAMPLE_DEMAND_CSV,
    DemandZoneClusterer,
    EmptyDemandDatasetError,
    InsufficientDemandPointsError,
    InvalidClusterConfigurationError,
    InvalidDemandRecordError,
    PILOT_BOUNDS,
    generate_sample_delivery_demand_csv,
    load_demand_records_from_csv,
    save_clustering_evaluation_report,
)


def main() -> None:
    print("=" * 72)
    print("TESTING STANDALONE K-MEANS DEMAND CLUSTERING (STEP 6.1)")
    print("=" * 72)

    # 1. Generate and verify the synthetic demonstration dataset
    print("\n[1] Generating & inspecting synthetic demonstration dataset")
    csv_path = generate_sample_delivery_demand_csv(
        csv_path=DEFAULT_SAMPLE_DEMAND_CSV,
        random_seed=42,
    )
    assert csv_path.exists(), f"Expected CSV at {csv_path}"
    records = load_demand_records_from_csv(csv_path)
    assert len(records) == 40, f"Expected 40 sample points, got {len(records)}"

    for idx, row in enumerate(records):
        assert row["data_source"] == "synthetic_demo", (
            f"Row #{idx} must have data_source='synthetic_demo', got {row['data_source']!r}"
        )
        lat = float(row["latitude"])
        lng = float(row["longitude"])
        demand = float(row["demand_units"])
        assert PILOT_BOUNDS["min_lat"] <= lat <= PILOT_BOUNDS["max_lat"], (
            f"Row #{idx} latitude {lat} outside pilot bounds"
        )
        assert PILOT_BOUNDS["min_lng"] <= lng <= PILOT_BOUNDS["max_lng"], (
            f"Row #{idx} longitude {lng} outside pilot bounds"
        )
        assert demand > 0, f"Row #{idx} demand must be positive"

    print(
        f"    Loaded {len(records)} rows from {csv_path.name} "
        f"(all rows tagged data_source='synthetic_demo' and inside pilot road-graph bounds)."
    )

    # 2. Fit K-Means on the demonstration dataset and verify summaries
    print("\n[2] Running DemandZoneClusterer (n_clusters=4, random_state=42)")
    clusterer = DemandZoneClusterer(n_clusters=4, random_state=42)
    result = clusterer.fit_predict(records)

    assert result["n_clusters"] == 4
    assert result["random_state"] == 42
    assert result["dataset_size"] == len(records)
    assert result["data_provenance"]["is_synthetic_demo"] is True

    clusters = result["clusters"]
    points = result["points"]
    assert len(clusters) == 4
    assert len(points) == len(records)

    # Verify point counts and demand totals match exactly
    sum_cluster_points = sum(c["point_count"] for c in clusters)
    sum_cluster_demand = round(sum(c["total_demand_units"] for c in clusters), 2)
    expected_total_demand = round(sum(float(r["demand_units"]) for r in records), 2)
    sum_demand_share = round(sum(c["demand_share_pct"] for c in clusters), 1)

    assert sum_cluster_points == len(records), (
        f"Cluster point count sum {sum_cluster_points} != {len(records)}"
    )
    assert math.isclose(sum_cluster_demand, expected_total_demand, abs_tol=1e-2), (
        f"Cluster demand sum {sum_cluster_demand} != {expected_total_demand}"
    )
    assert math.isclose(sum_demand_share, 100.0, abs_tol=0.2), (
        f"Demand share percentages sum to {sum_demand_share}, expected ~100.0"
    )

    # Verify internal clustering metrics are present and valid for k=4, N=40
    metrics = result["evaluation_metrics"]
    assert metrics["silhouette_score"] is not None
    assert -1.0 <= metrics["silhouette_score"] <= 1.0
    assert metrics["davies_bouldin_score"] is not None
    assert metrics["davies_bouldin_score"] >= 0.0
    assert metrics["metrics_omitted_reason"] is None

    # Save machine-readable evaluation report
    report_path = save_clustering_evaluation_report(
        result,
        report_path=DEFAULT_EVALUATION_REPORT_PATH,
        dataset_path=csv_path,
    )
    assert report_path.exists(), f"Expected evaluation report at {report_path}"
    print(f"    Saved evaluation report to: {report_path}")
    print(
        json.dumps(
            {
                "dataset_size": result["dataset_size"],
                "total_demand_units": result["total_demand_units"],
                "evaluation_metrics": result["evaluation_metrics"],
                "clusters": result["clusters"],
            },
            indent=2,
        )
    )

    # 3. Verify reproducibility with the same random seed
    print("\n[3] Testing reproducibility with identical random_state=42")
    repeat_clusterer = DemandZoneClusterer(n_clusters=4, random_state=42)
    repeat_result = repeat_clusterer.fit_predict(records)

    assert [p["cluster_id"] for p in result["points"]] == [
        p["cluster_id"] for p in repeat_result["points"]
    ], "Cluster assignments differed for identical random_state!"
    assert result["evaluation_metrics"] == repeat_result["evaluation_metrics"], (
        "Evaluation metrics differed for identical random_state!"
    )
    print("    Reproducibility verified: identical labels, centroids, and metrics.")

    # 4. Test invalid coordinates, non-positive demand values, and invalid priority
    print("\n[4] Testing invalid coordinates and invalid demand values")
    invalid_records_cases = [
        (
            [{"latitude": 102.0, "longitude": 91.88, "demand_units": 100, "priority": "High"}],
            "latitude > 90",
        ),
        (
            [{"latitude": 25.57, "longitude": -195.0, "demand_units": 100, "priority": "High"}],
            "longitude < -180",
        ),
        (
            [{"latitude": float("nan"), "longitude": 91.88, "demand_units": 100, "priority": "High"}],
            "NaN latitude",
        ),
        (
            [{"latitude": 25.57, "longitude": 91.88, "demand_units": 0, "priority": "High"}],
            "zero demand_units",
        ),
        (
            [{"latitude": 25.57, "longitude": 91.88, "demand_units": -50, "priority": "High"}],
            "negative demand_units",
        ),
        (
            [{"latitude": 25.57, "longitude": 91.88, "demand_units": True, "priority": "High"}],
            "boolean demand_units",
        ),
        (
            [{"latitude": 25.57, "longitude": 91.88, "demand_units": 100, "priority": "CriticalInvalid"}],
            "invalid priority tier",
        ),
    ]
    single_clusterer = DemandZoneClusterer(n_clusters=1, random_state=42)
    for bad_input, description in invalid_records_cases:
        try:
            single_clusterer.fit_predict(bad_input)
            raise AssertionError(f"Expected InvalidDemandRecordError for {description}")
        except InvalidDemandRecordError as err:
            print(f"    Correctly rejected ({description}): {err}")

    # 5. Test empty input, too many clusters, and invalid cluster config
    print("\n[5] Testing empty dataset and insufficient records for requested n_clusters")
    try:
        clusterer.fit_predict([])
        raise AssertionError("Expected EmptyDemandDatasetError for empty list")
    except EmptyDemandDatasetError as err:
        print(f"    Correctly rejected empty dataset: {err}")

    try:
        DemandZoneClusterer(n_clusters=5, random_state=42).fit_predict(records[:3])
        raise AssertionError("Expected InsufficientDemandPointsError when n_samples < n_clusters")
    except InsufficientDemandPointsError as err:
        print(f"    Correctly rejected too few records: {err}")

    try:
        DemandZoneClusterer(n_clusters=0, random_state=42)
        raise AssertionError("Expected InvalidClusterConfigurationError for n_clusters=0")
    except InvalidClusterConfigurationError as err:
        print(f"    Correctly rejected invalid n_clusters=0: {err}")

    # 6. Test metric precondition guards (k=1 and k=N)
    print("\n[6] Testing metric precondition guards (k=1 and k=N singleton clusters)")
    k1_res = DemandZoneClusterer(n_clusters=1, random_state=42).fit_predict(records[:6])
    assert k1_res["evaluation_metrics"]["silhouette_score"] is None
    assert k1_res["evaluation_metrics"]["davies_bouldin_score"] is None
    assert k1_res["evaluation_metrics"]["metrics_omitted_reason"] is not None
    print(f"    k=1 omitted metrics reason: {k1_res['evaluation_metrics']['metrics_omitted_reason']}")

    kn_res = DemandZoneClusterer(n_clusters=6, random_state=42).fit_predict(records[:6])
    assert kn_res["evaluation_metrics"]["silhouette_score"] is None
    assert kn_res["evaluation_metrics"]["davies_bouldin_score"] is None
    assert kn_res["evaluation_metrics"]["metrics_omitted_reason"] is not None
    print(f"    k=N omitted metrics reason: {kn_res['evaluation_metrics']['metrics_omitted_reason']}")

    print("\n" + "=" * 72)
    print("ALL DEMAND CLUSTERING TESTS PASSED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()

