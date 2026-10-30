from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, ndcg_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

from route_scoring import RoutePreferenceType, evaluate_candidate_routes

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ML_REPORT_PATH = BASE_DIR / "reports" / "route_ranking_ml_evaluation.json"
DEFAULT_ML_MODEL_ARTIFACT_PATH = BASE_DIR / "models" / "pairwise_route_ranker_v1.joblib"

FEATURE_NAMES: list[str] = [
    "distance_ratio_to_min",
    "duration_ratio_to_min",
    "major_arterial_fraction",
    "secondary_collector_fraction",
    "local_road_fraction",
    "intersection_density_per_km",
    "bridge_tunnel_fraction",
    "pref_shortest_x_dist_ratio",
    "pref_fastest_x_time_ratio",
    "pref_balanced_x_combined_ratio",
    "pref_accessibility_x_hierarchy_penalty",
]


def extract_route_feature_vector(
    candidate_eval: dict[str, Any],
    preference: RoutePreferenceType,
    min_distance_km: float,
    min_duration_min: float,
) -> np.ndarray:
    """
    Extract an 11-dimensional numerical feature vector x_i for candidate route i
    conditioned on the query's minimum distance, minimum duration, and preference mode
    ('shortest', 'fastest', 'balanced', or 'accessibility').
    """
    ev = candidate_eval.get("evidence", {})
    dist_km = max(0.0, float(ev.get("distance_km", 0.0)))
    dur_min = max(0.0, float(ev.get("estimated_duration_min", 0.0)))

    dist_ratio = (dist_km / min_distance_km) if min_distance_km > 0 and dist_km > 0 else 1.0
    time_ratio = (dur_min / min_duration_min) if min_duration_min > 0 and dur_min > 0 else 1.0

    rc = ev.get("road_class_breakdown_pct", {})
    major_frac = float(rc.get("major_arterial", 0.0)) / 100.0
    secondary_frac = float(rc.get("secondary_collector", 0.0)) / 100.0
    local_frac = float(rc.get("local_unclassified", 0.0)) / 100.0

    int_density = float(ev.get("intersection_density_per_km", 0.0))
    num_nodes = max(1, int(ev.get("num_nodes", 1)))
    bridges = int(ev.get("bridges_count", 0))
    tunnels = int(ev.get("tunnels_count", 0))
    struct_frac = min(1.0, float(bridges + tunnels) / float(num_nodes))

    is_shortest = 1.0 if preference == "shortest" else 0.0
    is_fastest = 1.0 if preference == "fastest" else 0.0
    is_balanced = 1.0 if preference == "balanced" else 0.0
    is_accessibility = 1.0 if preference == "accessibility" else 0.0

    # Hierarchy penalty for accessibility mode: lower when major arterial share is high
    hierarchy_penalty = (1.0 - major_frac) + 0.6 * local_frac + 0.25 * time_ratio

    return np.array(
        [
            dist_ratio,
            time_ratio,
            major_frac,
            secondary_frac,
            local_frac,
            int_density / 10.0,  # scaled to ~[0, 2]
            struct_frac,
            is_shortest * dist_ratio,
            is_fastest * time_ratio,
            is_balanced * (0.5 * dist_ratio + 0.5 * time_ratio),
            is_accessibility * hierarchy_penalty,
        ],
        dtype=np.float64,
    )


def _synthetic_NonLinear_utility(
    candidate_eval: dict[str, Any],
    preference: RoutePreferenceType,
    min_distance_km: float,
    min_duration_min: float,
    rng: np.random.Generator,
    noise_std: float = 0.8,
) -> float:
    """
    Synthetic benchmark utility function incorporating realistic non-linear logistics factors
    (junction turn-delay penalty, local-road heavy-vehicle penalty, and preference weights)
    used strictly to generate reproducible query-grouped synthetic benchmark scenarios
    when real-world observed telemetry is unavailable.
    """
    ev = candidate_eval.get("evidence", {})
    dist_km = max(0.01, float(ev.get("distance_km", 1.0)))
    dur_min = max(0.01, float(ev.get("estimated_duration_min", 1.0)))
    rc = ev.get("road_class_breakdown_pct", {})
    major_frac = float(rc.get("major_arterial", 0.0)) / 100.0
    local_frac = float(rc.get("local_unclassified", 0.0)) / 100.0
    int_density = float(ev.get("intersection_density_per_km", 4.0))

    s_dist = 100.0 * (min_distance_km / dist_km)
    s_time = 100.0 * (min_duration_min / dur_min)
    # Non-linear junction complexity & narrow local-road penalty for relief trucks
    hierarchy_bonus = 14.0 * major_frac - 16.0 * (local_frac ** 1.3) - 0.45 * max(0.0, int_density - 4.0)

    if preference == "shortest":
        base_u = 0.88 * s_dist + 0.08 * s_time + 0.4 * hierarchy_bonus
    elif preference == "fastest":
        base_u = 0.08 * s_dist + 0.88 * s_time + 0.4 * hierarchy_bonus
    elif preference == "accessibility":
        base_u = 0.25 * s_dist + 0.35 * s_time + 2.2 * hierarchy_bonus
    else:
        base_u = 0.44 * s_dist + 0.44 * s_time + 1.0 * hierarchy_bonus

    noise = float(rng.normal(0.0, noise_std)) if noise_std > 0 else 0.0
    return float(base_u + noise)


def generate_synthetic_benchmark_queries(
    n_Corridors: int = 60,
    random_state: int = 42,
) -> list[dict[str, Any]]:
    """
    Generate a reproducible set of multi-candidate route queries modeled on realistic
    mountain highway corridor trade-offs (Shortest vs. Estimated Fastest vs. Balanced Collector)
    across all 4 routing preferences ('shortest', 'fastest', 'balanced', 'accessibility').
    Every query is explicitly tagged with `data_source = "synthetic_simulation_benchmark"`.
    """
    rng = np.random.default_rng(random_state)
    preferences: list[RoutePreferenceType] = [
        "shortest",
        "fastest",
        "balanced",
        "accessibility",
    ]
    queries: list[dict[str, Any]] = []

    for corridor_idx in range(n_Corridors):
        spatial_block_id = f"corridor_block_{corridor_idx // 3}"
        base_dist_km = float(rng.uniform(12.0, 68.0))
        shortest_speed_kph = float(rng.uniform(22.0, 31.0))
        shortest_dur_min = (base_dist_km / shortest_speed_kph) * 60.0

        # Fastest route is slightly longer (+3% to +16%) but uses higher-speed arterial roads (33-43 km/h)
        detour_factor = float(rng.uniform(1.03, 1.16))
        fastest_dist_km = base_dist_km * detour_factor
        fastest_speed_kph = float(rng.uniform(33.0, 43.0))
        fastest_dur_min = (fastest_dist_km / fastest_speed_kph) * 60.0

        # Secondary balanced route lies in between
        mid_dist_km = base_dist_km * float(rng.uniform(1.01, 1.08))
        mid_speed_kph = float(rng.uniform(28.0, 36.0))
        mid_dur_min = (mid_dist_km / mid_speed_kph) * 60.0

        s_major = float(rng.uniform(20.0, 48.0))
        s_sec = float(rng.uniform(25.0, 45.0))
        s_loc = max(0.0, 100.0 - s_major - s_sec)

        f_major = float(rng.uniform(55.0, 82.0))
        f_sec = float(rng.uniform(12.0, 32.0))
        f_loc = max(0.0, 100.0 - f_major - f_sec)

        m_major = float(rng.uniform(40.0, 65.0))
        m_sec = float(rng.uniform(20.0, 40.0))
        m_loc = max(0.0, 100.0 - m_major - m_sec)

        raw_candidates = [
            {
                "route_id": "shortest",
                "route_type": "shortest",
                "distance_km": round(base_dist_km, 2),
                "estimated_duration_min": round(shortest_dur_min, 1),
                "num_nodes": max(15, int(base_dist_km * rng.uniform(5.2, 7.5))),
                "edge_summary": {
                    "road_hierarchy_score": round(0.75 * s_major + 0.45 * s_sec + 0.15 * s_loc, 1),
                    "road_class_breakdown_pct": {
                        "major_arterial": round(s_major, 1),
                        "secondary_collector": round(s_sec, 1),
                        "local_unclassified": round(s_loc, 1),
                    },
                    "imputed_speed_edges_pct": 99.8,
                    "bridges_count": int(rng.integers(0, 4)),
                    "tunnels_count": 0,
                },
            },
            {
                "route_id": "estimated_fastest",
                "route_type": "estimated_fastest",
                "distance_km": round(fastest_dist_km, 2),
                "estimated_duration_min": round(fastest_dur_min, 1),
                "num_nodes": max(12, int(fastest_dist_km * rng.uniform(3.4, 5.0))),
                "edge_summary": {
                    "road_hierarchy_score": round(0.75 * f_major + 0.45 * f_sec + 0.15 * f_loc, 1),
                    "road_class_breakdown_pct": {
                        "major_arterial": round(f_major, 1),
                        "secondary_collector": round(f_sec, 1),
                        "local_unclassified": round(f_loc, 1),
                    },
                    "imputed_speed_edges_pct": 99.8,
                    "bridges_count": int(rng.integers(1, 6)),
                    "tunnels_count": 0,
                },
            },
            {
                "route_id": "balanced_collector",
                "route_type": "balanced_collector",
                "distance_km": round(mid_dist_km, 2),
                "estimated_duration_min": round(mid_dur_min, 1),
                "num_nodes": max(14, int(mid_dist_km * rng.uniform(4.2, 6.0))),
                "edge_summary": {
                    "road_hierarchy_score": round(0.75 * m_major + 0.45 * m_sec + 0.15 * m_loc, 1),
                    "road_class_breakdown_pct": {
                        "major_arterial": round(m_major, 1),
                        "secondary_collector": round(m_sec, 1),
                        "local_unclassified": round(m_loc, 1),
                    },
                    "imputed_speed_edges_pct": 99.8,
                    "bridges_count": int(rng.integers(0, 5)),
                    "tunnels_count": 0,
                },
            },
        ]

        for pref in preferences:
            det_eval = evaluate_candidate_routes(
                candidates=raw_candidates,
                preference=pref,
                origin_snap_m=15.0,
                destination_snap_m=22.0,
            )
            cands_eval = det_eval["candidates"]
            min_d = min(float(c["evidence"]["distance_km"]) for c in cands_eval)
            min_t = min(float(c["evidence"]["estimated_duration_min"]) for c in cands_eval)

            utilities: dict[str, float] = {}
            features_by_id: dict[str, np.ndarray] = {}
            for c_item in cands_eval:
                rid = str(c_item["route_id"])
                utilities[rid] = _synthetic_NonLinear_utility(
                    c_item, pref, min_d, min_t, rng=rng, noise_std=0.6
                )
                features_by_id[rid] = extract_route_feature_vector(
                    c_item, pref, min_d, min_t
                )

            queries.append(
                {
                    "query_id": f"q_{corridor_idx}_{pref}",
                    "spatial_group_id": spatial_block_id,
                    "preference": pref,
                    "data_source": "synthetic_simulation_benchmark",
                    "candidates": cands_eval,
                    "features_by_id": features_by_id,
                    "target_utilities": utilities,
                }
            )

    return queries


class PairwiseRouteRanker:
    """
    Experimental Pairwise Route-Ranking ML Model (RankLinear / LogisticRegression on
    pairwise feature differences x_A - x_B).

    Academic Integrity & Provenance:
    - Trained with strict spatial query-group splitting (GroupShuffleSplit) so no
      corridor or origin-destination query ever leaks across train and test sets.
    - Enforces antisymmetric pairwise augmentation ((x_A - x_B, 1) and (x_B - x_A, 0)).
    - Explicitly flags whether the training labels come from `synthetic_simulation_benchmark`
      or `observed_telemetry`.
    """

    def __init__(self, random_state: int = 42, c_reg: float = 1.0) -> None:
        self.random_state = int(random_state)
        self.c_reg = float(c_reg)
        self.scaler = StandardScaler()
        self.model = LogisticRegression(
            C=self.c_reg,
            fit_intercept=False,  # Zero intercept guaranteed by antisymmetric pairwise difference
            random_state=self.random_state,
            max_iter=500,
        )
        self.is_fitted = False
        self.is_synthetic_benchmark = True
        self.evaluation_summary: dict[str, Any] | None = None

    @staticmethod
    def _build_pairwise_arrays(
        queries: list[dict[str, Any]],
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        X_rows: list[np.ndarray] = []
        y_rows: list[int] = []
        groups: list[str] = []

        for q in queries:
            cands = q["candidates"]
            feats = q["features_by_id"]
            utils = q["target_utilities"]
            grp = str(q["spatial_group_id"])

            n_c = len(cands)
            for i in range(n_c):
                for j in range(i + 1, n_c):
                    id_a = str(cands[i]["route_id"])
                    id_b = str(cands[j]["route_id"])
                    u_a = float(utils[id_a])
                    u_b = float(utils[id_b])
                    if abs(u_a - u_b) < 1e-6:
                        continue
                    diff_ab = feats[id_a] - feats[id_b]
                    label_ab = 1 if u_a > u_b else 0

                    # Antisymmetric pair augmentation
                    X_rows.append(diff_ab)
                    y_rows.append(label_ab)
                    groups.append(grp)

                    X_rows.append(-diff_ab)
                    y_rows.append(1 - label_ab)
                    groups.append(grp)

        return np.vstack(X_rows), np.array(y_rows, dtype=np.int64), groups

    def fit_and_evaluate(
        self,
        queries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Split queries by `spatial_group_id` into train (60%), validation (20%), and
        held-out test (20%) sets, fit the pairwise model on train, and compare against
        three deterministic baselines on the held-out test set.
        """
        dataset = (
            queries
            if queries is not None
            else generate_synthetic_benchmark_queries(
                n_Corridors=60, random_state=self.random_state
            )
        )
        all_sources = sorted({str(q.get("data_source", "synthetic_simulation_benchmark")) for q in dataset})
        self.is_synthetic_benchmark = any("synthetic" in s for s in all_sources)

        group_labels = np.array([str(q["spatial_group_id"]) for q in dataset])
        gss_outer = GroupShuffleSplit(
            n_splits=1, test_size=0.20, random_state=self.random_state
        )
        train_val_idx, test_idx = next(gss_outer.split(dataset, groups=group_labels))

        train_val_queries = [dataset[i] for i in train_val_idx]
        test_queries = [dataset[i] for i in test_idx]

        tv_groups = np.array([str(q["spatial_group_id"]) for q in train_val_queries])
        gss_inner = GroupShuffleSplit(
            n_splits=1, test_size=0.25, random_state=self.random_state
        )
        train_sub_idx, val_sub_idx = next(
            gss_inner.split(train_val_queries, groups=tv_groups)
        )

        train_queries = [train_val_queries[i] for i in train_sub_idx]
        val_queries = [train_val_queries[i] for i in val_sub_idx]

        # Verify zero group leakage across splits
        train_grp_set = {q["spatial_group_id"] for q in train_queries}
        val_grp_set = {q["spatial_group_id"] for q in val_queries}
        test_grp_set = {q["spatial_group_id"] for q in test_queries}
        assert train_grp_set.isdisjoint(test_grp_set), "Data leakage between train and test groups!"
        assert val_grp_set.isdisjoint(test_grp_set), "Data leakage between val and test groups!"
        assert train_grp_set.isdisjoint(val_grp_set), "Data leakage between train and val groups!"

        X_train, y_train, _ = self._build_pairwise_arrays(train_queries)
        X_val, y_val, _ = self._build_pairwise_arrays(val_queries)
        X_test, y_test, _ = self._build_pairwise_arrays(test_queries)

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)

        self.model.fit(X_train_scaled, y_train)
        self.is_fitted = True

        train_pair_acc = round(float(accuracy_score(y_train, self.model.predict(X_train_scaled))), 4)
        val_pair_acc = round(float(accuracy_score(y_val, self.model.predict(X_val_scaled))), 4)
        test_pair_acc = round(float(accuracy_score(y_test, self.model.predict(X_test_scaled))), 4)

        # Evaluate query-level ranking metrics on held-out test set across 5 methods
        comparison = {
            "shortest_distance_heuristic": self._evaluate_ranking_method(
                test_queries, method="shortest_only"
            ),
            "fastest_time_heuristic": self._evaluate_ranking_method(
                test_queries, method="fastest_only"
            ),
            "road_hierarchy_heuristic": self._evaluate_ranking_method(
                test_queries, method="hierarchy_only"
            ),
            "deterministic_multi_criteria_baseline": self._evaluate_ranking_method(
                test_queries, method="deterministic_baseline"
            ),
            "pairwise_logistic_ranker_ml": self._evaluate_ranking_method(
                test_queries, method="ml_ranker"
            ),
        }
        comparison["pairwise_logistic_ranker_ml"]["pairwise_accuracy"] = test_pair_acc

        coef_weights = {
            name: round(float(w), 4)
            for name, w in zip(FEATURE_NAMES, self.model.coef_[0])
        }

        self.evaluation_summary = {
            "model_id": "pairwise_linear_ranker_v1_synthetic_demo",
            "model_type": "Pairwise LogisticRegression (antisymmetric difference ranker, fit_intercept=False)",
            "model_artifact_path": str(DEFAULT_ML_MODEL_ARTIFACT_PATH),
            "status": (
                "experimental_synthetic_benchmark_only"
                if self.is_synthetic_benchmark
                else "validated_on_observed_data"
            ),
            "is_synthetic_benchmark": self.is_synthetic_benchmark,
            "used_for_primary_recommendation": False,
            "provenance_note": (
                "Evaluated on query-grouped synthetic multi-criteria mountain corridor benchmark "
                "scenarios (data_source='synthetic_simulation_benchmark') across all 4 preferences "
                "('shortest', 'fastest', 'balanced', 'accessibility'). Validates 11-feature extraction, "
                "GroupShuffleSplit zero-leakage partitioning, and NDCG/pairwise metrics. "
                "Do NOT claim real-world generalization without observed fleet telemetry labels."
            ),
            "supported_preferences": ["shortest", "fastest", "balanced", "accessibility"],
            "feature_names": list(FEATURE_NAMES),
            "split_verification": {
                "splitting_strategy": "GroupShuffleSplit by spatial_group_id (60% train / 20% val / 20% test)",
                "train_queries": len(train_queries),
                "validation_queries": len(val_queries),
                "test_queries": len(test_queries),
                "train_pairs": int(len(y_train)),
                "validation_pairs": int(len(y_val)),
                "test_pairs": int(len(y_test)),
                "zero_group_overlap_verified": True,
            },
            "pairwise_accuracy_by_split": {
                "train": train_pair_acc,
                "validation": val_pair_acc,
                "test": test_pair_acc,
            },
            "held_out_test_comparison": comparison,
            "learned_feature_weights": coef_weights,
        }
        return self.evaluation_summary

    def save_model_artifact(
        self,
        artifact_path: str | Path = DEFAULT_ML_MODEL_ARTIFACT_PATH,
    ) -> Path:
        """Persist the fitted StandardScaler, LogisticRegression model, and evaluation summary."""
        if not self.is_fitted:
            self.fit_and_evaluate()
        out_path = Path(artifact_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model_id": "pairwise_linear_ranker_v1_synthetic_demo",
            "random_state": self.random_state,
            "c_reg": self.c_reg,
            "feature_names": list(FEATURE_NAMES),
            "scaler": self.scaler,
            "model": self.model,
            "is_synthetic_benchmark": self.is_synthetic_benchmark,
            "evaluation_summary": self.evaluation_summary,
        }
        joblib.dump(payload, out_path)
        return out_path

    @classmethod
    def load_or_train(
        cls,
        artifact_path: str | Path = DEFAULT_ML_MODEL_ARTIFACT_PATH,
        report_path: str | Path = DEFAULT_ML_REPORT_PATH,
        random_state: int = 42,
    ) -> "PairwiseRouteRanker":
        """Load persisted model artifact if compatible with current FEATURE_NAMES; otherwise train and save."""
        path_obj = Path(artifact_path).resolve()
        if path_obj.exists():
            try:
                payload = joblib.load(path_obj)
                if payload.get("feature_names") == list(FEATURE_NAMES):
                    instance = cls(
                        random_state=int(payload.get("random_state", random_state)),
                        c_reg=float(payload.get("c_reg", 1.0)),
                    )
                    instance.scaler = payload["scaler"]
                    instance.model = payload["model"]
                    instance.is_fitted = True
                    instance.is_synthetic_benchmark = bool(
                        payload.get("is_synthetic_benchmark", True)
                    )
                    instance.evaluation_summary = payload.get("evaluation_summary")
                    return instance
            except Exception:
                pass

        instance = cls(random_state=random_state)
        summary = instance.fit_and_evaluate()
        instance.save_model_artifact(path_obj)
        save_ml_evaluation_report(summary, report_path)
        return instance

    def _score_query_candidates_ml(
        self,
        candidates: list[dict[str, Any]],
        preference: RoutePreferenceType,
    ) -> dict[str, float]:
        """Compute continuous pairwise win-probability scores for each candidate in a query."""
        if not candidates:
            return {}
        if not self.is_fitted or len(candidates) == 1:
            return {str(c["route_id"]): 1.0 for c in candidates}

        min_d = min(
            max(0.01, float(c.get("evidence", {}).get("distance_km", 1.0)))
            for c in candidates
        )
        min_t = min(
            max(0.01, float(c.get("evidence", {}).get("estimated_duration_min", 1.0)))
            for c in candidates
        )
        feats = {
            str(c["route_id"]): extract_route_feature_vector(c, preference, min_d, min_t)
            for c in candidates
        }
        ids = [str(c["route_id"]) for c in candidates]
        win_probs: dict[str, float] = {rid: 0.0 for rid in ids}

        for i, id_a in enumerate(ids):
            probs_a: list[float] = []
            for j, id_b in enumerate(ids):
                if i == j:
                    continue
                diff = (feats[id_a] - feats[id_b]).reshape(1, -1)
                diff_scaled = self.scaler.transform(diff)
                prob_a_beats_b = float(self.model.predict_proba(diff_scaled)[0, 1])
                probs_a.append(prob_a_beats_b)
            win_probs[id_a] = round(float(np.mean(probs_a)) if probs_a else 1.0, 4)

        return win_probs

    def _evaluate_ranking_method(
        self,
        queries: list[dict[str, Any]],
        method: str,
    ) -> dict[str, float]:
        top1_matches = 0
        ndcg_at_2_list: list[float] = []
        ndcg_at_all_list: list[float] = []
        correct_pairs = 0
        total_pairs = 0

        for q in queries:
            cands = q["candidates"]
            pref: RoutePreferenceType = q["preference"]
            utils = q["target_utilities"]
            ids = [str(c["route_id"]) for c in cands]

            if method == "shortest_only":
                pred_scores = {
                    str(c["route_id"]): -float(c["evidence"]["distance_km"])
                    for c in cands
                }
            elif method == "fastest_only":
                pred_scores = {
                    str(c["route_id"]): -float(c["evidence"]["estimated_duration_min"])
                    for c in cands
                }
            elif method == "hierarchy_only":
                pred_scores = {
                    str(c["route_id"]): float(
                        c.get("component_scores", {}).get("road_hierarchy_score", 50.0)
                    )
                    for c in cands
                }
            elif method == "deterministic_baseline":
                pred_scores = {
                    str(c["route_id"]): float(c["overall_score"])
                    for c in cands
                }
            else:
                pred_scores = self._score_query_candidates_ml(cands, pref)

            best_true_id = max(ids, key=lambda rid: float(utils[rid]))
            best_pred_id = max(ids, key=lambda rid: float(pred_scores[rid]))
            if best_true_id == best_pred_id:
                top1_matches += 1

            # Pairwise concordance
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    ia, ib = ids[i], ids[j]
                    if abs(utils[ia] - utils[ib]) < 1e-6:
                        continue
                    total_pairs += 1
                    if (utils[ia] - utils[ib]) * (pred_scores[ia] - pred_scores[ib]) > 0:
                        correct_pairs += 1

            # Shift utilities to non-negative relevance gains for NDCG
            min_u = min(float(utils[rid]) for rid in ids)
            y_true = np.array([[float(utils[rid]) - min_u + 1.0 for rid in ids]])
            y_score = np.array([[float(pred_scores[rid]) for rid in ids]])
            ndcg_at_2_list.append(float(ndcg_score(y_true, y_score, k=2)))
            ndcg_at_all_list.append(float(ndcg_score(y_true, y_score, k=None)))

        n_q = max(1, len(queries))
        return {
            "pairwise_accuracy": round(correct_pairs / max(1, total_pairs), 4),
            "top1_recommendation_agreement": round(top1_matches / n_q, 4),
            "ndcg_at_2": round(float(np.mean(ndcg_at_2_list)), 4),
            "ndcg_at_3": round(float(np.mean(ndcg_at_all_list)), 4),
        }

    def rank_live_evaluation_candidates(
        self,
        deterministic_evaluation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Produce the separate `ml_ranking` metadata object for a live route query.
        Never overwrites or replaces the deterministic baseline score.
        """
        if not self.is_fitted:
            self.fit_and_evaluate()

        cands = deterministic_evaluation.get("candidates", [])
        pref: RoutePreferenceType = deterministic_evaluation.get("preference", "balanced")
        routes_identical = bool(deterministic_evaluation.get("routes_are_identical", False))

        eval_metrics_summary: dict[str, Any] = {}
        if self.evaluation_summary:
            comp = self.evaluation_summary.get("held_out_test_comparison", {})
            ml_comp = comp.get("pairwise_logistic_ranker_ml", {})
            det_comp = comp.get("deterministic_multi_criteria_baseline", {})
            eval_metrics_summary = {
                "splitting_strategy": self.evaluation_summary.get(
                    "split_verification", {}
                ).get("splitting_strategy", "GroupShuffleSplit (60/20/20)"),
                "test_pairwise_accuracy": ml_comp.get("pairwise_accuracy"),
                "test_top1_agreement": ml_comp.get("top1_recommendation_agreement"),
                "test_ndcg_at_3": ml_comp.get("ndcg_at_3"),
                "deterministic_baseline_pairwise_accuracy": det_comp.get("pairwise_accuracy"),
                "deterministic_baseline_ndcg_at_3": det_comp.get("ndcg_at_3"),
            }

        if not cands:
            return {
                "status": "experimental_synthetic_benchmark_only",
                "is_synthetic_benchmark": True,
                "used_for_primary_recommendation": False,
                "model_id": "pairwise_linear_ranker_v1_synthetic_demo",
                "provenance_warning": (
                    "Experimental pairwise ML ranker trained on synthetic corridor benchmark pairs. "
                    "Primary route recommendation uses the deterministic multi-criteria baseline."
                ),
                "predicted_ranking": [],
                "win_probabilities": {},
                "agreement_with_deterministic_baseline": True,
                "evaluation_metrics_summary": eval_metrics_summary,
            }

        min_d = min(
            max(0.01, float(c.get("evidence", {}).get("distance_km", 1.0)))
            for c in cands
        )
        min_t = min(
            max(0.01, float(c.get("evidence", {}).get("estimated_duration_min", 1.0)))
            for c in cands
        )
        feature_values_by_route: dict[str, dict[str, float]] = {}
        for c_item in cands:
            rid = str(c_item["route_id"])
            vec = extract_route_feature_vector(c_item, pref, min_d, min_t)
            feature_values_by_route[rid] = {
                fname: round(float(val), 4)
                for fname, val in zip(FEATURE_NAMES, vec)
            }

        win_probs = self._score_query_candidates_ml(cands, pref)
        if routes_identical:
            predicted_order = [str(c["route_id"]) for c in cands]
            agrees = True
        else:
            predicted_order = sorted(
                [str(c["route_id"]) for c in cands],
                key=lambda rid: (-win_probs.get(rid, 0.0), rid),
            )
            det_top = deterministic_evaluation.get("recommended_route_id")
            agrees = bool(predicted_order and predicted_order[0] == det_top)

        return {
            "status": "experimental_synthetic_benchmark_only",
            "is_synthetic_benchmark": True,
            "used_for_primary_recommendation": False,
            "model_id": "pairwise_linear_ranker_v1_synthetic_demo",
            "provenance_warning": (
                "Experimental pairwise ML ranker trained on synthetic corridor benchmark pairs "
                "(data_source='synthetic_simulation_benchmark') to validate the ML ranking pipeline. "
                "Primary recommendation is governed by the deterministic multi-criteria formula."
            ),
            "predicted_ranking": predicted_order,
            "win_probabilities": win_probs,
            "agreement_with_deterministic_baseline": agrees,
            "feature_values_by_route": feature_values_by_route,
            "evaluation_metrics_summary": eval_metrics_summary,
        }


def save_ml_evaluation_report(
    report_data: dict[str, Any],
    report_path: str | Path = DEFAULT_ML_REPORT_PATH,
) -> Path:
    out_path = Path(report_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    return out_path


if __name__ == "__main__":
    ranker = PairwiseRouteRanker(random_state=42)
    summary = ranker.fit_and_evaluate()
    model_path = ranker.save_model_artifact()
    saved = save_ml_evaluation_report(summary)
    print(f"Saved ML model artifact to: {model_path}")
    print(f"Saved ML route ranking evaluation report to: {saved}")
    print(json.dumps(summary, indent=2))

