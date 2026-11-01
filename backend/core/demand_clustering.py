from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score

BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if Path(__file__).resolve().parent.name in ("core", "services", "scripts", "tests")
    else Path(__file__).resolve().parent
)
DEFAULT_SAMPLE_DEMAND_CSV = BASE_DIR / "data" / "sample_delivery_demand.csv"
DEFAULT_EVALUATION_REPORT_PATH = (
    BASE_DIR / "reports" / "demand_clustering_evaluation.json"
)

# Coordinate Reference Systems:
# - EPSG:4326: WGS 84 geographic coordinates (latitude, longitude in decimal degrees).
# - EPSG:32646: WGS 84 / UTM zone 46N (metric easting/northing in metres), covering 90°E to 96°E
#   in the Northern Hemisphere, which directly spans Meghalaya (~91.57°E to ~92.07°E).
GEOGRAPHIC_CRS = "EPSG:4326"
PROJECTED_METRIC_CRS = "EPSG:32646"

VALID_PRIORITIES = {"Low", "Normal", "High", "Emergency"}
PRIORITY_WEIGHT_MAP = {
    "Low": 1.0,
    "Normal": 2.0,
    "High": 3.0,
    "Emergency": 4.0,
}

# Bounds of the cleaned Shillong-Sohra road network (from road_data_audit.json)
PILOT_BOUNDS = {
    "min_lat": 25.195198,
    "max_lat": 25.644707,
    "min_lng": 91.571629,
    "max_lng": 92.068831,
}


class DemandClusteringError(Exception):
    """Base exception for demand clustering errors."""


class EmptyDemandDatasetError(DemandClusteringError, ValueError):
    """Raised when the input demand dataset contains zero records."""


class InsufficientDemandPointsError(DemandClusteringError, ValueError):
    """Raised when the number of demand records is smaller than n_clusters."""


class InvalidDemandRecordError(DemandClusteringError, ValueError):
    """Raised when a demand record has invalid coordinates, non-positive demand, or invalid priority."""


class InvalidClusterConfigurationError(DemandClusteringError, ValueError):
    """Raised when n_clusters or random_state configuration is invalid."""


def _validate_finite_float(value: Any, field_name: str, record_index: int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        try:
            if isinstance(value, str) and value.strip():
                numeric = float(value.strip())
            else:
                raise InvalidDemandRecordError(
                    f"Record #{record_index}: '{field_name}' must be a numeric value, got {value!r}."
                )
        except ValueError as exc:
            raise InvalidDemandRecordError(
                f"Record #{record_index}: '{field_name}' must be a numeric value, got {value!r}."
            ) from exc
    else:
        numeric = float(value)

    if not math.isfinite(numeric):
        raise InvalidDemandRecordError(
            f"Record #{record_index}: '{field_name}' must be finite (not NaN or infinity), got {value!r}."
        )
    return numeric


def generate_sample_delivery_demand_csv(
    csv_path: str | Path = DEFAULT_SAMPLE_DEMAND_CSV,
    random_seed: int = 42,
) -> Path:
    """
    Generate a reproducible, clearly labelled synthetic demonstration dataset of delivery
    demand points inside the downloaded Shillong-Sohra road-network bounding box.

    Every row is explicitly tagged with `data_source = "synthetic_demo"`.
    """
    output_path = Path(csv_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(random_seed)

    # 4 geographically plausible settlement corridors inside the Shillong-Sohra road graph bounds
    # (Lat: 25.1952 to 25.6447, Lng: 91.5716 to 92.0688)
    anchor_zones = [
        {
            "name": "Shillong Plateau Urban & Upper Shillong",
            "center_lat": 25.5740,
            "center_lng": 91.8880,
            "lat_spread": 0.018,
            "lng_spread": 0.022,
            "count": 12,
            "demand_range": (120, 480),
            "priorities": ["Normal", "High", "Emergency", "High"],
        },
        {
            "name": "Sohra / Cherrapunji Southern Escarpment",
            "center_lat": 25.2800,
            "center_lng": 91.7300,
            "lat_spread": 0.016,
            "lng_spread": 0.018,
            "count": 10,
            "demand_range": (150, 520),
            "priorities": ["High", "Emergency", "Normal", "High"],
        },
        {
            "name": "Mairang West Khasi Highland Corridor",
            "center_lat": 25.5600,
            "center_lng": 91.6450,
            "lat_spread": 0.016,
            "lng_spread": 0.020,
            "count": 10,
            "demand_range": (80, 340),
            "priorities": ["Low", "Normal", "High", "Normal"],
        },
        {
            "name": "Pynursla - Southern Border Approach Corridor",
            "center_lat": 25.3150,
            "center_lng": 91.9100,
            "lat_spread": 0.020,
            "lng_spread": 0.022,
            "count": 8,
            "demand_range": (100, 390),
            "priorities": ["Normal", "High", "Low", "Emergency"],
        },
    ]

    rows: list[dict[str, Any]] = []
    for zone in anchor_zones:
        for i in range(zone["count"]):
            lat = float(rng.normal(zone["center_lat"], zone["lat_spread"]))
            lng = float(rng.normal(zone["center_lng"], zone["lng_spread"]))
            # Clamp strictly inside the verified road network bounding box with a safety margin
            lat = max(PILOT_BOUNDS["min_lat"] + 0.01, min(PILOT_BOUNDS["max_lat"] - 0.01, lat))
            lng = max(PILOT_BOUNDS["min_lng"] + 0.01, min(PILOT_BOUNDS["max_lng"] - 0.01, lng))

            low_d, high_d = zone["demand_range"]
            demand_units = int(rng.integers(low_d, high_d + 1))
            priority = zone["priorities"][i % len(zone["priorities"])]

            rows.append(
                {
                    "latitude": round(lat, 6),
                    "longitude": round(lng, 6),
                    "demand_units": demand_units,
                    "priority": priority,
                    "data_source": "synthetic_demo",
                }
            )

    fieldnames = ["latitude", "longitude", "demand_units", "priority", "data_source"]
    with open(output_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def load_demand_records_from_csv(csv_path: str | Path = DEFAULT_SAMPLE_DEMAND_CSV) -> list[dict[str, Any]]:
    """Load delivery-demand records from a CSV file."""
    path = Path(csv_path).resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Demand dataset CSV file not found at: {path}")

    with open(path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader)


class DemandZoneClusterer:
    """
    Standalone K-Means demand-zone clustering module for the Meghalaya pilot region.

    Coordinate Handling & Projection Choice:
    - Raw (latitude, longitude) degrees are angular coordinates on an ellipsoid; at ~25.4°N
      (Meghalaya), 1° of longitude (~100.6 km) is ~9.2% shorter than 1° of latitude (~110.8 km).
      Fitting Euclidean K-Means directly on degree values distorts east-west vs. north-south
      distances and produces non-metric inertia.
    - This class projects coordinates from WGS84 (EPSG:4326) into WGS 84 / UTM zone 46N
      (EPSG:32646, metric easting/northing in metres) using pyproj before fitting K-Means,
      and transforms fitted cluster centres back to (latitude, longitude) for map/API use.
    - Limitation: Planar Euclidean distances in UTM zone 46N accurately measure straight-line
      horizontal separation across the pilot area, but do not account for mountain road-network
      detours, canyon barriers, or elevation gradients.
    """

    def __init__(
        self,
        n_clusters: int = 4,
        random_state: int = 42,
        projected_crs: str = PROJECTED_METRIC_CRS,
    ) -> None:
        if isinstance(n_clusters, bool) or not isinstance(n_clusters, int) or n_clusters < 1:
            raise InvalidClusterConfigurationError(
                f"n_clusters must be a positive integer >= 1, got {n_clusters!r}."
            )
        if isinstance(random_state, bool) or not isinstance(random_state, int):
            raise InvalidClusterConfigurationError(
                f"random_state must be an integer, got {random_state!r}."
            )

        self.n_clusters = n_clusters
        self.random_state = random_state
        self.projected_crs = projected_crs
        self._to_metric = Transformer.from_crs(
            GEOGRAPHIC_CRS, self.projected_crs, always_xy=True
        )
        self._to_geographic = Transformer.from_crs(
            self.projected_crs, GEOGRAPHIC_CRS, always_xy=True
        )

    @staticmethod
    def validate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate delivery-demand records and return normalized copies."""
        if not isinstance(records, list):
            raise InvalidDemandRecordError("Input records must be provided as a list of dictionaries.")
        if len(records) == 0:
            raise EmptyDemandDatasetError("Demand dataset is empty; at least one demand record is required.")

        validated: list[dict[str, Any]] = []
        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                raise InvalidDemandRecordError(
                    f"Record #{idx}: expected a dict, got {type(rec).__name__}."
                )

            raw_lat = rec.get("latitude", rec.get("lat"))
            raw_lng = rec.get("longitude", rec.get("lng"))
            if raw_lat is None:
                raise InvalidDemandRecordError(f"Record #{idx}: missing 'latitude'.")
            if raw_lng is None:
                raise InvalidDemandRecordError(f"Record #{idx}: missing 'longitude'.")

            lat = _validate_finite_float(raw_lat, "latitude", idx)
            lng = _validate_finite_float(raw_lng, "longitude", idx)

            if lat < -90.0 or lat > 90.0:
                raise InvalidDemandRecordError(
                    f"Record #{idx}: latitude {lat} is outside valid geographic bounds [-90.0, 90.0]."
                )
            if lng < -180.0 or lng > 180.0:
                raise InvalidDemandRecordError(
                    f"Record #{idx}: longitude {lng} is outside valid geographic bounds [-180.0, 180.0]."
                )

            raw_demand = rec.get("demand_units")
            if raw_demand is None:
                raise InvalidDemandRecordError(f"Record #{idx}: missing 'demand_units'.")
            demand_units = _validate_finite_float(raw_demand, "demand_units", idx)
            if demand_units <= 0.0:
                raise InvalidDemandRecordError(
                    f"Record #{idx}: 'demand_units' must be strictly positive (> 0), got {demand_units}."
                )

            raw_priority = rec.get("priority", "Normal")
            if not isinstance(raw_priority, str) or raw_priority.strip() not in VALID_PRIORITIES:
                raise InvalidDemandRecordError(
                    f"Record #{idx}: invalid priority {raw_priority!r}. Must be one of {sorted(VALID_PRIORITIES)}."
                )
            priority = raw_priority.strip()

            data_source = str(rec.get("data_source", "synthetic_demo")).strip() or "synthetic_demo"

            validated.append(
                {
                    "point_index": idx,
                    "latitude": round(lat, 6),
                    "longitude": round(lng, 6),
                    "demand_units": round(float(demand_units), 2),
                    "priority": priority,
                    "priority_weight": PRIORITY_WEIGHT_MAP[priority],
                    "data_source": data_source,
                }
            )

        return validated

    def fit_predict(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Validate records, project coordinates to EPSG:32646 (metres), fit K-Means,
        and return point assignments, cluster summaries, and internal clustering metrics.
        """
        validated = self.validate_records(records)
        n_samples = len(validated)

        if n_samples < self.n_clusters:
            raise InsufficientDemandPointsError(
                f"Cannot fit {self.n_clusters} clusters on only {n_samples} demand records "
                f"(require n_samples >= n_clusters)."
            )

        lats = np.array([r["latitude"] for r in validated], dtype=np.float64)
        lngs = np.array([r["longitude"] for r in validated], dtype=np.float64)
        demands = np.array([r["demand_units"] for r in validated], dtype=np.float64)

        # Project (longitude, latitude) -> (easting_m, northing_m) in EPSG:32646
        eastings_m, northings_m = self._to_metric.transform(lngs, lats)
        coords_metric = np.column_stack([eastings_m, northings_m])

        kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=10,
        )
        labels = kmeans.fit_predict(coords_metric)
        centers_metric = kmeans.cluster_centers_

        # Inverse-project cluster centres back to (longitude, latitude) in EPSG:4326
        center_lngs, center_lats = self._to_geographic.transform(
            centers_metric[:, 0], centers_metric[:, 1]
        )

        total_dataset_demand = float(np.sum(demands))
        assigned_points: list[dict[str, Any]] = []

        for idx, rec in enumerate(validated):
            cid = int(labels[idx])
            dist_m = float(
                math.hypot(
                    coords_metric[idx, 0] - centers_metric[cid, 0],
                    coords_metric[idx, 1] - centers_metric[cid, 1],
                )
            )
            assigned_points.append(
                {
                    **rec,
                    "cluster_id": cid,
                    "easting_m": round(float(coords_metric[idx, 0]), 2),
                    "northing_m": round(float(coords_metric[idx, 1]), 2),
                    "distance_to_cluster_center_m": round(dist_m, 2),
                }
            )

        # Build per-cluster summaries
        cluster_summaries: list[dict[str, Any]] = []
        for cid in range(self.n_clusters):
            member_indices = np.where(labels == cid)[0]
            point_count = int(len(member_indices))
            cluster_demand = float(np.sum(demands[member_indices])) if point_count > 0 else 0.0
            mean_demand = (cluster_demand / point_count) if point_count > 0 else 0.0
            demand_share_pct = (
                (cluster_demand / total_dataset_demand) * 100.0
                if total_dataset_demand > 0
                else 0.0
            )

            # Demand-weighted centroid in metric space, transformed back to (lat, lng)
            if point_count > 0 and cluster_demand > 0:
                weights = demands[member_indices]
                weighted_easting = float(np.average(coords_metric[member_indices, 0], weights=weights))
                weighted_northing = float(np.average(coords_metric[member_indices, 1], weights=weights))
                w_lng, w_lat = self._to_geographic.transform(weighted_easting, weighted_northing)
            else:
                w_lat = float(center_lats[cid])
                w_lng = float(center_lngs[cid])

            priority_counts = {p: 0 for p in ("Low", "Normal", "High", "Emergency")}
            weighted_priority_demand = 0.0
            member_dists: list[float] = []

            for m_idx in member_indices:
                p_label = validated[int(m_idx)]["priority"]
                priority_counts[p_label] += 1
                weighted_priority_demand += (
                    validated[int(m_idx)]["demand_units"]
                    * validated[int(m_idx)]["priority_weight"]
                )
                member_dists.append(assigned_points[int(m_idx)]["distance_to_cluster_center_m"])

            mean_priority_weight = (
                weighted_priority_demand / cluster_demand if cluster_demand > 0 else 0.0
            )

            cluster_summaries.append(
                {
                    "cluster_id": cid,
                    "center_lat": round(float(center_lats[cid]), 6),
                    "center_lng": round(float(center_lngs[cid]), 6),
                    "center_easting_m": round(float(centers_metric[cid, 0]), 2),
                    "center_northing_m": round(float(centers_metric[cid, 1]), 2),
                    "demand_weighted_center_lat": round(float(w_lat), 6),
                    "demand_weighted_center_lng": round(float(w_lng), 6),
                    "point_count": point_count,
                    "total_demand_units": round(cluster_demand, 2),
                    "mean_demand_units": round(mean_demand, 2),
                    "demand_share_pct": round(demand_share_pct, 2),
                    "demand_weighted_priority_index": round(mean_priority_weight, 2),
                    "priority_breakdown": priority_counts,
                    "mean_distance_to_center_m": round(float(np.mean(member_dists)), 2) if member_dists else 0.0,
                    "max_distance_to_center_m": round(float(np.max(member_dists)), 2) if member_dists else 0.0,
                }
            )

        # Evaluate internal clustering metrics only when mathematically valid:
        # Silhouette and Davies-Bouldin scores require 2 <= n_distinct_labels <= n_samples - 1.
        distinct_labels = len(set(int(lbl) for lbl in labels))
        if 2 <= distinct_labels <= (n_samples - 1):
            sil_score: float | None = round(
                float(silhouette_score(coords_metric, labels, metric="euclidean")), 4
            )
            db_score: float | None = round(
                float(davies_bouldin_score(coords_metric, labels)), 4
            )
            omitted_reason: str | None = None
        else:
            sil_score = None
            db_score = None
            if distinct_labels < 2:
                omitted_reason = (
                    f"Silhouette and Davies-Bouldin scores are mathematically undefined when "
                    f"n_clusters={self.n_clusters} (distinct clusters={distinct_labels} < 2)."
                )
            else:
                omitted_reason = (
                    f"Silhouette and Davies-Bouldin scores are mathematically undefined when "
                    f"every point forms its own singleton cluster (distinct clusters={distinct_labels} == n_samples={n_samples})."
                )

        data_sources = sorted({r["data_source"] for r in validated})

        return {
            "model": "KMeans (scikit-learn)",
            "n_clusters": self.n_clusters,
            "random_state": self.random_state,
            "dataset_size": n_samples,
            "total_demand_units": round(total_dataset_demand, 2),
            "data_provenance": {
                "data_sources": data_sources,
                "is_synthetic_demo": all(src == "synthetic_demo" for src in data_sources),
                "provenance_note": (
                    "Demonstration dataset generated with a fixed seed (synthetic_demo). "
                    "Not real-world delivery records or observed disaster demand."
                ),
            },
            "coordinate_projection": {
                "input_crs": GEOGRAPHIC_CRS,
                "clustering_crs": self.projected_crs,
                "clustering_units": "metres (UTM Zone 46N easting/northing)",
                "explanation": (
                    "Geographic (latitude, longitude) coordinates are projected to EPSG:32646 "
                    "(WGS 84 / UTM zone 46N) in metres prior to K-Means fitting so Euclidean "
                    "distances reflect horizontal metric separation rather than distorted angular degrees."
                ),
                "limitations": [
                    "Planar Euclidean distance in UTM Zone 46N measures straight-line horizontal separation and does not account for mountain road-network detours, canyon/river barriers, or steep elevation gradients.",
                    "K-Means partitions spatial demand points into convex Voronoi cells and does not predict disaster risk or real-time road accessibility.",
                ],
            },
            "evaluation_metrics": {
                "inertia_m2": round(float(kmeans.inertia_), 2),
                "silhouette_score": sil_score,
                "davies_bouldin_score": db_score,
                "metrics_omitted_reason": omitted_reason,
                "interpretation_note": (
                    "Silhouette score ([-1, 1], higher indicates tighter/more separated clusters) and "
                    "Davies-Bouldin score ([0, inf), lower indicates better separation) are internal "
                    "unsupervised spatial cohesion metrics computed on projected metric coordinates. "
                    "They do NOT measure classification accuracy, real-world demand prediction accuracy, "
                    "or disaster-risk validity."
                ),
            },
            "clusters": cluster_summaries,
            "points": assigned_points,
        }


def save_clustering_evaluation_report(
    clustering_result: dict[str, Any],
    report_path: str | Path = DEFAULT_EVALUATION_REPORT_PATH,
    dataset_path: str | Path | None = DEFAULT_SAMPLE_DEMAND_CSV,
) -> Path:
    """Save a machine-readable JSON evaluation report for the demand clustering run."""
    out_path = Path(report_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report_payload = {
        "module": "backend/demand_clustering.py",
        "stage": "Step 6.1 — Standalone K-Means Demand-Zone Clustering",
        "dataset_path": str(Path(dataset_path).resolve()) if dataset_path else None,
        "model": clustering_result["model"],
        "n_clusters": clustering_result["n_clusters"],
        "random_state": clustering_result["random_state"],
        "dataset_size": clustering_result["dataset_size"],
        "total_demand_units": clustering_result["total_demand_units"],
        "data_provenance": clustering_result["data_provenance"],
        "coordinate_projection": clustering_result["coordinate_projection"],
        "evaluation_metrics": clustering_result["evaluation_metrics"],
        "cluster_summaries": clustering_result["clusters"],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    return out_path


if __name__ == "__main__":
    csv_file = generate_sample_delivery_demand_csv()
    records = load_demand_records_from_csv(csv_file)
    clusterer = DemandZoneClusterer(n_clusters=4, random_state=42)
    result = clusterer.fit_predict(records)
    report_file = save_clustering_evaluation_report(result, dataset_path=csv_file)
    print(f"Sample demand CSV saved to: {csv_file}")
    print(f"Evaluation report saved to: {report_file}")

