from __future__ import annotations

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
for _p in [_ROOT, _ROOT / 'core', _ROOT / 'services']:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


import json
import math
from typing import Any

from fastapi.testclient import TestClient

from main import app


def main() -> None:
    print("=" * 72)
    print("TESTING FASTAPI DEMAND-ZONES ENDPOINT (POST /api/demand-zones)")
    print("=" * 72)

    client = TestClient(app)

    # 1. Test default POST /api/demand-zones (defaults: n_clusters=4, random_state=42)
    print("\n[1] Testing POST /api/demand-zones with default parameters (n_clusters=4, random_state=42)")
    res_default = client.post("/api/demand-zones", json={})
    assert res_default.status_code == 200, (
        f"Expected HTTP 200, got {res_default.status_code}: {res_default.text}"
    )
    data = res_default.json()

    assert data["model"] == "KMeans (scikit-learn)"
    assert data["n_clusters"] == 4
    assert data["random_state"] == 42
    assert data["dataset_size"] == 40
    assert data["total_demand_units"] == 11205.0

    # Verify data provenance explicitly marks records as synthetic_demo
    prov = data["data_provenance"]
    assert prov["is_synthetic_demo"] is True
    assert prov["data_sources"] == ["synthetic_demo"]
    assert "synthetic_demo" in prov["provenance_note"]
    assert "Not real-world delivery records" in prov["provenance_note"]

    # Verify coordinate projection metadata
    proj = data["coordinate_projection"]
    assert proj["input_crs"] == "EPSG:4326"
    assert proj["clustering_crs"] == "EPSG:32646"

    # Verify evaluation metrics match standalone model output
    metrics = data["evaluation_metrics"]
    assert metrics["silhouette_score"] == 0.868
    assert metrics["davies_bouldin_score"] == 0.1817
    assert metrics["metrics_omitted_reason"] is None

    # Verify clusters and point assignments
    clusters = data["clusters"]
    points = data["points"]
    assert len(clusters) == 4
    assert len(points) == 40
    assert sum(c["point_count"] for c in clusters) == 40
    assert math.isclose(
        sum(c["total_demand_units"] for c in clusters), 11205.0, abs_tol=1e-2
    )
    assert all(p["data_source"] == "synthetic_demo" for p in points)

    sample_response_preview = {
        "model": data["model"],
        "n_clusters": data["n_clusters"],
        "random_state": data["random_state"],
        "dataset_size": data["dataset_size"],
        "total_demand_units": data["total_demand_units"],
        "data_provenance": data["data_provenance"],
        "coordinate_projection": data["coordinate_projection"],
        "evaluation_metrics": data["evaluation_metrics"],
        "clusters": data["clusters"],
        "sample_first_2_points": data["points"][:2],
    }
    print(json.dumps(sample_response_preview, indent=2))

    # 2. Test custom valid cluster count (n_clusters=3, random_state=42)
    print("\n[2] Testing POST /api/demand-zones with custom n_clusters=3")
    res_k3 = client.post(
        "/api/demand-zones", json={"n_clusters": 3, "random_state": 42}
    )
    assert res_k3.status_code == 200
    k3_data = res_k3.json()
    assert k3_data["n_clusters"] == 3
    assert len(k3_data["clusters"]) == 3
    assert sum(c["point_count"] for c in k3_data["clusters"]) == 40
    print(
        f"    HTTP 200 OK | k=3 silhouette={k3_data['evaluation_metrics']['silhouette_score']} | "
        f"davies_bouldin={k3_data['evaluation_metrics']['davies_bouldin_score']}"
    )

    # 3. Test boundary cluster count k=1 (metrics omitted gracefully)
    print("\n[3] Testing POST /api/demand-zones with n_clusters=1 (silhouette/DB omitted)")
    res_k1 = client.post("/api/demand-zones", json={"n_clusters": 1})
    assert res_k1.status_code == 200
    k1_data = res_k1.json()
    assert k1_data["evaluation_metrics"]["silhouette_score"] is None
    assert k1_data["evaluation_metrics"]["davies_bouldin_score"] is None
    assert k1_data["evaluation_metrics"]["metrics_omitted_reason"] is not None
    print(
        f"    HTTP 200 OK | k=1 metrics omitted: {k1_data['evaluation_metrics']['metrics_omitted_reason']}"
    )

    # 4. Test invalid cluster counts & invalid inputs
    print("\n[4] Testing invalid cluster counts and malformed request payloads")
    invalid_cases: list[tuple[str, dict[str, Any], str]] = [
        (
            "n_clusters=0",
            {"n_clusters": 0},
            "invalid_cluster_configuration",
        ),
        (
            "negative n_clusters=-3",
            {"n_clusters": -3},
            "invalid_cluster_configuration",
        ),
        (
            "n_clusters=50 (> 40 records)",
            {"n_clusters": 50},
            "insufficient_demand_points",
        ),
        (
            "boolean n_clusters=True",
            {"n_clusters": True},
            "invalid_cluster_configuration",
        ),
        (
            "string n_clusters='four'",
            {"n_clusters": "four"},
            "invalid_cluster_configuration",
        ),
        (
            "float n_clusters=3.5",
            {"n_clusters": 3.5},
            "invalid_cluster_configuration",
        ),
        (
            "unexpected extra field",
            {"n_clusters": 4, "unknown_param": 123},
            "invalid_cluster_configuration",
        ),
    ]

    for label, payload, expected_error_code in invalid_cases:
        bad_res = client.post("/api/demand-zones", json=payload)
        assert bad_res.status_code == 422, (
            f"Expected HTTP 422 for {label}, got {bad_res.status_code}: {bad_res.text}"
        )
        err_body = bad_res.json()
        assert err_body["error"] == expected_error_code, (
            f"Expected error={expected_error_code!r} for {label}, got {err_body}"
        )
        assert "Traceback" not in bad_res.text
        print(f"    {label} -> HTTP {bad_res.status_code}: {json.dumps(err_body)}")

    print("\n" + "=" * 72)
    print("ALL DEMAND-ZONES FASTAPI TESTS PASSED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    main()

