from __future__ import annotations

import json
import math

from route_ranking_ml import (
    DEFAULT_ML_REPORT_PATH,
    PairwiseRouteRanker,
    generate_synthetic_benchmark_queries,
    save_ml_evaluation_report,
)


def main() -> None:
    print("=" * 72)
    print("TESTING EXPERIMENTAL PAIRWISE ROUTE-RANKING ML PIPELINE (STAGE 3)")
    print("=" * 72)

    # 1. Generate synthetic benchmark queries and verify provenance
    print("\n[1] Generating query-grouped synthetic corridor benchmark dataset")
    queries = generate_synthetic_benchmark_queries(n_Corridors=60, random_state=42)
    assert len(queries) == 180, f"Expected 180 queries (60 corridors x 3 preferences), got {len(queries)}"
    assert all(q["data_source"] == "synthetic_simulation_benchmark" for q in queries)
    print(f"    Generated {len(queries)} queries across 20 spatial blocks (all tagged 'synthetic_simulation_benchmark').")

    # 2. Verify antisymmetric pairwise array balance
    print("\n[2] Verifying antisymmetric pairwise feature difference balance")
    X_pairs, y_pairs, groups = PairwiseRouteRanker._build_pairwise_arrays(queries[:10])
    assert X_pairs.shape[0] == len(y_pairs) == len(groups)
    assert math.isclose(float(y_pairs.mean()), 0.5, abs_tol=1e-6), (
        f"Expected exact 50/50 class balance from antisymmetric pairs, got {y_pairs.mean()}"
    )
    print(f"    Pairwise array shape={X_pairs.shape}, class balance mean={y_pairs.mean():.4f}.")

    # 3. Fit and evaluate PairwiseRouteRanker and verify zero group leakage
    print("\n[3] Fitting PairwiseRouteRanker with GroupShuffleSplit (60/20/20)")
    ranker = PairwiseRouteRanker(random_state=42)
    report = ranker.fit_and_evaluate(queries)

    assert report["is_synthetic_benchmark"] is True
    assert report["used_for_primary_recommendation"] is False
    assert report["split_verification"]["zero_group_overlap_verified"] is True

    comp = report["held_out_test_comparison"]
    ml_metrics = comp["pairwise_logistic_ranker_ml"]
    det_metrics = comp["deterministic_multi_criteria_baseline"]
    short_metrics = comp["shortest_distance_heuristic"]
    fast_metrics = comp["fastest_time_heuristic"]

    assert 0.0 <= ml_metrics["pairwise_accuracy"] <= 1.0
    assert 0.0 <= ml_metrics["ndcg_at_2"] <= 1.0
    # Verify multi-criteria methods outperform single-objective heuristics across mixed preferences
    assert det_metrics["pairwise_accuracy"] > short_metrics["pairwise_accuracy"]
    assert det_metrics["pairwise_accuracy"] > fast_metrics["pairwise_accuracy"]
    assert ml_metrics["pairwise_accuracy"] > short_metrics["pairwise_accuracy"]
    assert ml_metrics["pairwise_accuracy"] > fast_metrics["pairwise_accuracy"]

    # 4. Verify reproducibility with identical random_state=42
    print("\n[4] Verifying reproducibility with random_state=42")
    ranker_repeat = PairwiseRouteRanker(random_state=42)
    report_repeat = ranker_repeat.fit_and_evaluate(queries)
    assert report["pairwise_accuracy_by_split"] == report_repeat["pairwise_accuracy_by_split"]
    assert report["learned_feature_weights"] == report_repeat["learned_feature_weights"]
    print("    Reproducibility verified: identical split accuracies and learned weights.")

    # 5. Save evaluation report to backend/reports/route_ranking_ml_evaluation.json
    saved_path = save_ml_evaluation_report(report, DEFAULT_ML_REPORT_PATH)
    assert saved_path.exists()
    print(f"\n[5] Saved evaluation report to: {saved_path}")
    print(json.dumps(report, indent=2))

    print("\n" + "=" * 72)
    print("ALL PAIRWISE ROUTE-RANKING ML TESTS PASSED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()

