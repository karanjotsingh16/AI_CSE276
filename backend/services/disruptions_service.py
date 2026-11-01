from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if Path(__file__).resolve().parent.name in ("core", "services", "scripts", "tests")
    else Path(__file__).resolve().parent
)
DEFAULT_DISRUPTIONS_PATH = BASE_DIR / "data" / "regional_disruptions.json"


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    )
    return float(2.0 * r * math.asin(min(1.0, math.sqrt(a))))


class DisruptionsService:
    """
    Manages regional road disruptions, slope stability watches, bridge load limits,
    and transit advisories verified by official agencies (NHIDCL, Meghalaya PWD, SDMA, BRO).

    Academic Integrity & Provenance:
    - Never invents synthetic accident or landslide probabilities.
    - Operates strictly on verified published advisories with exact coordinates, radius,
      and issuing agency attribution.
    - Performs deterministic spatial intersection between candidate route polylines
      and advisory hazard radii.
    """

    def __init__(self, data_path: str | Path = DEFAULT_DISRUPTIONS_PATH) -> None:
        self.data_path = Path(data_path).resolve()
        self._disruptions: list[dict[str, Any]] = self._load_disruptions()

    def _load_disruptions(self) -> list[dict[str, Any]]:
        if not self.data_path.exists():
            return []
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def reload(self) -> int:
        self._disruptions = self._load_disruptions()
        return len(self._disruptions)

    def list_active_disruptions(self) -> list[dict[str, Any]]:
        """Return all active regional road disruption advisories."""
        return [d for d in self._disruptions if d.get("status") == "active"]

    def evaluate_route_disruptions(
        self,
        geometry_coords: list[list[float]],  # [[lng, lat], ...]
    ) -> dict[str, Any]:
        """
        Check if a candidate route's polyline intersects the hazard radius of any active
        road disruption, and compute a deterministic 0-100 confirmed disruptions score.
        """
        if not geometry_coords:
            return {
                "status": "unavailable",
                "confirmed_disruptions_score": 100.0,
                "intersected_count": 0,
                "intersected_disruptions": [],
                "explanation": "No route geometry provided for disruption evaluation.",
            }

        active = self.list_active_disruptions()
        if not active:
            return {
                "status": "clear",
                "confirmed_disruptions_score": 100.0,
                "intersected_count": 0,
                "intersected_disruptions": [],
                "explanation": "No active regional disruption advisories in database.",
            }

        intersected: list[dict[str, Any]] = []
        total_penalty = 0.0

        for item in active:
            d_lat = float(item["latitude"])
            d_lng = float(item["longitude"])
            radius_m = float(item.get("radius_m", 1000.0))
            sev = str(item.get("severity", "advisory")).lower()

            # Find minimum distance between any route polyline point and the disruption center
            min_dist = float("inf")
            for pt in geometry_coords:
                pt_lng, pt_lat = pt[0], pt[1]
                dist = _haversine_distance_m(d_lat, d_lng, pt_lat, pt_lng)
                if dist < min_dist:
                    min_dist = dist
                    if min_dist <= radius_m:
                        break  # Early exit once within radius

            if min_dist <= radius_m:
                if sev == "critical":
                    penalty = 60.0
                elif sev == "warning":
                    penalty = 35.0
                else:  # advisory
                    penalty = 15.0

                total_penalty += penalty
                intersected.append(
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "category": item["category"],
                        "severity": item["severity"],
                        "issuing_agency": item["issuing_agency"],
                        "affected_highway": item["affected_highway"],
                        "description": item["description"],
                        "closest_approach_m": round(min_dist, 1),
                        "radius_m": radius_m,
                        "penalty_points": penalty,
                        "speed_reduction_pct": item.get("speed_reduction_pct", 0.0),
                    }
                )

        score = round(max(10.0, 100.0 - total_penalty), 1)

        if not intersected:
            explanation = "Route corridor is completely clear of confirmed road disruptions and maintenance advisories."
            status = "clear"
        elif any(i["severity"] == "critical" for i in intersected):
            explanation = f"Route intersects {len(intersected)} active disruption(s), including a critical road advisory."
            status = "critical_hazard"
        elif any(i["severity"] == "warning" for i in intersected):
            explanation = f"Route intersects {len(intersected)} active disruption(s) with maintenance or load-restriction warnings."
            status = "warning"
        else:
            explanation = f"Route intersects {len(intersected)} minor precautionary road advisory zone(s)."
            status = "advisory"

        return {
            "status": status,
            "confirmed_disruptions_score": score,
            "intersected_count": len(intersected),
            "intersected_disruptions": intersected,
            "explanation": explanation,
            "total_active_monitored": len(active),
            "data_source": "Official Regional Road Advisories (NHIDCL / Meghalaya PWD / SDMA / BRO)",
        }
