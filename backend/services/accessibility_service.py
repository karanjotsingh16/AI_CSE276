"""Road Accessibility Monitoring & Field Reporting Service.

Implements Module D (Road Accessibility Monitoring) and Module E (Field Reporting System)
for the NER SmartRoute platform.

Features:
- Road segment status management: open, restricted, blocked, unknown.
- Field incident reporting: road_blockage, flood, landslide, bridge_damage, road_damage, other.
- Status verification workflow: pending -> verified, rejected, resolved.
- Immutable audit trail of all status transitions and administrative reviews.
- Persistent SQLite storage with thread safety and ACID compliance.
- Spatial corridor proximity matching for automatic segment linkage.
- Photo upload handling with file type and size validation.

Academic Integrity & Operating Rules:
- Never automatically mark a road segment as blocked based solely on an unverified report.
- Field reports begin in 'pending' status until verified by an authorized reviewer.
- All status transitions require an actor and rationale recorded in the audit log.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BACKEND_DIR = (
    Path(__file__).resolve().parent.parent
    if Path(__file__).resolve().parent.name in ("core", "services", "scripts", "tests")
    else Path(__file__).resolve().parent
)
DATA_DIR = BACKEND_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DEFAULT_DB_PATH = DATA_DIR / "accessibility.db"

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

VALID_SEGMENT_STATUSES = {"open", "restricted", "blocked", "unknown"}
VALID_INCIDENT_STATUSES = {"pending", "verified", "rejected", "resolved"}
VALID_INCIDENT_TYPES = {
    "road_blockage",
    "flood",
    "landslide",
    "bridge_damage",
    "road_damage",
    "other",
}
VALID_SEVERITIES = {"low", "moderate", "severe", "critical"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _distance_point_to_segment_m(
    p_lat: float, p_lng: float, a_lat: float, a_lng: float, b_lat: float, b_lng: float
) -> float:
    # Approximate projected distance
    d_ab = _haversine_distance_m(a_lat, a_lng, b_lat, b_lng)
    if d_ab < 1e-6:
        return _haversine_distance_m(p_lat, p_lng, a_lat, a_lng)

    # Use Euclidean projection on local tangent plane in meters
    cos_lat = math.cos(math.radians((a_lat + b_lat) / 2.0))
    ax, ay = 0.0, 0.0
    bx = (b_lng - a_lng) * 111320.0 * cos_lat
    by = (b_lat - a_lat) * 110540.0
    px = (p_lng - a_lng) * 111320.0 * cos_lat
    py = (p_lat - a_lat) * 110540.0

    ab_sq = bx * bx + by * by
    if ab_sq < 1e-6:
        return math.hypot(px, py)

    t = max(0.0, min(1.0, (px * bx + py * by) / ab_sq))
    proj_x = t * bx
    proj_y = t * by
    return math.hypot(px - proj_x, py - proj_y)


# Initial seed data for key monitored corridors across Meghalaya & NER
SEED_ROAD_SEGMENTS = [
    {
        "segment_id": "SEG-EKH-NH06-01",
        "name": "NH-6 Shillong - Umiam Corridor",
        "road_class": "trunk",
        "district": "Ri-Bhoi / East Khasi Hills",
        "state": "Meghalaya",
        "status": "restricted",
        "restriction_details": "Umiam Dam bridge single-lane load limit (max 10T). Heavy vehicles routed via Shillong Bypass.",
        "coordinates": [
            [25.6601, 91.8980],
            [25.6420, 91.9050],
            [25.6010, 91.8990],
            [25.5788, 91.8933],
        ],
    },
    {
        "segment_id": "SEG-EKH-SH05-01",
        "name": "Shillong - Cherrapunji (Sohra) Arterial",
        "road_class": "primary",
        "district": "East Khasi Hills",
        "state": "Meghalaya",
        "status": "open",
        "restriction_details": "Dense valley fog during early mornings; two-lane bitumen surface open.",
        "coordinates": [
            [25.5788, 91.8933],
            [25.5100, 91.8500],
            [25.4200, 91.7800],
            [25.2800, 91.7300],
        ],
    },
    {
        "segment_id": "SEG-WKH-NH106-01",
        "name": "NH-106 Shillong - Mairang - Nongstoin",
        "road_class": "primary",
        "district": "West Khasi Hills",
        "state": "Meghalaya",
        "status": "open",
        "restriction_details": "Regular two-lane vehicular movement permitted; caution on sharp hairpin curves.",
        "coordinates": [
            [25.5788, 91.8933],
            [25.5600, 91.7500],
            [25.5650, 91.6400],
            [25.5200, 91.2700],
        ],
    },
    {
        "segment_id": "SEG-EJH-NH06-02",
        "name": "NH-6 Sonapur - Ratacherra Ghat Corridor",
        "road_class": "trunk",
        "district": "East Jaintia Hills",
        "state": "Meghalaya",
        "status": "restricted",
        "restriction_details": "Post-monsoon hill-cutting and single-lane convoy control by NHIDCL.",
        "coordinates": [
            [25.1000, 92.3500],
            [25.0700, 92.3800],
            [25.0300, 92.4200],
            [24.9800, 92.4900],
        ],
    },
    {
        "segment_id": "SEG-WJH-SH03-01",
        "name": "Pynursla - Dawki Border Corridor",
        "road_class": "secondary",
        "district": "East Khasi Hills / West Jaintia Hills",
        "state": "Meghalaya",
        "status": "open",
        "restriction_details": "Dawki bridge structural evaluation completed; tourist and freight flow normal.",
        "coordinates": [
            [25.3000, 91.9000],
            [25.2400, 91.9500],
            [25.1900, 92.0100],
            [25.1850, 92.0200],
        ],
    },
    {
        "segment_id": "SEG-RBH-BYPASS-01",
        "name": "Shillong Eastern Bypass (Umsning - Mawryngkneng)",
        "road_class": "primary",
        "district": "Ri-Bhoi / East Khasi Hills",
        "state": "Meghalaya",
        "status": "open",
        "restriction_details": "Bypasses Shillong city congestion for transit freight to Silchar and Tripura.",
        "coordinates": [
            [25.7500, 91.8900],
            [25.6800, 91.9500],
            [25.5900, 92.0500],
            [25.5400, 92.0700],
        ],
    },
]


class AccessibilityService:
    """Manages road segment accessibility statuses, field incident reports, and the audit log."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_database(self) -> None:
        """Create schema and seed baseline road segments if not already present."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS road_segments (
                    segment_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    road_class TEXT NOT NULL,
                    district TEXT NOT NULL,
                    state TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('open', 'restricted', 'blocked', 'unknown')),
                    restriction_details TEXT,
                    coordinates_json TEXT NOT NULL,
                    last_inspected_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_reports (
                    report_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    incident_type TEXT NOT NULL CHECK(incident_type IN ('road_blockage', 'flood', 'landslide', 'bridge_damage', 'road_damage', 'other')),
                    severity TEXT NOT NULL CHECK(severity IN ('low', 'moderate', 'severe', 'critical')),
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    district TEXT NOT NULL,
                    location_name TEXT NOT NULL,
                    reporter_name TEXT NOT NULL,
                    reporter_role TEXT NOT NULL,
                    contact_number TEXT,
                    photo_url TEXT,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'verified', 'rejected', 'resolved')),
                    associated_segment_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (associated_segment_id) REFERENCES road_segments(segment_id) ON DELETE SET NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accessibility_audit_log (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL CHECK(entity_type IN ('incident', 'road_segment')),
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    review_notes TEXT,
                    timestamp TEXT NOT NULL
                );
                """
            )

            # Seed initial road segments if empty
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM road_segments;")
            count = cursor.fetchone()[0]
            if count == 0:
                now_iso = _utc_now_iso()
                for seg in SEED_ROAD_SEGMENTS:
                    cursor.execute(
                        """
                        INSERT INTO road_segments (
                            segment_id, name, road_class, district, state,
                            status, restriction_details, coordinates_json,
                            last_inspected_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            seg["segment_id"],
                            seg["name"],
                            seg["road_class"],
                            seg["district"],
                            seg["state"],
                            seg["status"],
                            seg["restriction_details"],
                            json.dumps(seg["coordinates"]),
                            now_iso,
                            now_iso,
                        ),
                    )
                    # Initial audit entry
                    cursor.execute(
                        """
                        INSERT INTO accessibility_audit_log (
                            entity_type, entity_id, action, previous_status,
                            new_status, actor, review_notes, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            "road_segment",
                            seg["segment_id"],
                            "seeded",
                            None,
                            seg["status"],
                            "System Initializer",
                            "Official baseline corridor initialization",
                            now_iso,
                        ),
                    )
            conn.commit()

    def list_segments(
        self, district: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List monitored road corridors, optionally filtered by district or status."""
        query = "SELECT * FROM road_segments WHERE 1=1"
        params: List[Any] = []
        if district:
            query += " AND district LIKE ?"
            params.append(f"%{district}%")
        if status:
            if status not in VALID_SEGMENT_STATUSES:
                raise ValueError(f"Invalid segment status '{status}'. Must be one of {VALID_SEGMENT_STATUSES}")
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY segment_id ASC;"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["coordinates"] = json.loads(d.pop("coordinates_json"))
                results.append(d)
            return results

    def get_segment(self, segment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single road segment by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM road_segments WHERE segment_id = ?;", (segment_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["coordinates"] = json.loads(d.pop("coordinates_json"))
            return d

    def find_nearest_segment(
        self, lat: float, lng: float, max_distance_m: float = 3000.0
    ) -> Tuple[Optional[str], float]:
        """Find the nearest road segment corridor within max_distance_m."""
        segments = self.list_segments()
        nearest_id = None
        min_dist = float("inf")

        for seg in segments:
            coords = seg["coordinates"]
            for i in range(len(coords) - 1):
                a_lat, a_lng = coords[i]
                b_lat, b_lng = coords[i + 1]
                dist = _distance_point_to_segment_m(lat, lng, a_lat, a_lng, b_lat, b_lng)
                if dist < min_dist:
                    min_dist = dist
                    nearest_id = seg["segment_id"]

        if min_dist <= max_distance_m:
            return nearest_id, min_dist
        return None, min_dist

    def update_segment_status(
        self,
        segment_id: str,
        new_status: str,
        actor: str,
        restriction_details: Optional[str] = None,
        review_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a road segment's operational status and record an immutable audit entry."""
        if new_status not in VALID_SEGMENT_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {sorted(VALID_SEGMENT_STATUSES)}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM road_segments WHERE segment_id = ?;", (segment_id,))
            row = cursor.fetchone()
            if not row:
                raise KeyError(f"Road segment '{segment_id}' not found.")

            prev_status = row["status"]
            now_iso = _utc_now_iso()

            updated_details = restriction_details if restriction_details is not None else row["restriction_details"]
            cursor.execute(
                """
                UPDATE road_segments
                SET status = ?, restriction_details = ?, updated_at = ?, last_inspected_at = ?
                WHERE segment_id = ?;
                """,
                (new_status, updated_details, now_iso, now_iso, segment_id),
            )

            cursor.execute(
                """
                INSERT INTO accessibility_audit_log (
                    entity_type, entity_id, action, previous_status,
                    new_status, actor, review_notes, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    "road_segment",
                    segment_id,
                    "status_updated",
                    prev_status,
                    new_status,
                    actor or "Authorized Official",
                    review_notes or f"Manual status transition to {new_status}",
                    now_iso,
                ),
            )
            conn.commit()

        updated = self.get_segment(segment_id)
        assert updated is not None
        return updated

    def submit_incident_report(
        self,
        title: str,
        description: str,
        incident_type: str,
        severity: str,
        latitude: float,
        longitude: float,
        district: str,
        location_name: str,
        reporter_name: str,
        reporter_role: str = "field_worker",
        contact_number: Optional[str] = None,
        photo_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a new field incident report. Always starts in 'pending' status."""
        if incident_type not in VALID_INCIDENT_TYPES:
            raise ValueError(f"Invalid incident_type '{incident_type}'. Must be one of {sorted(VALID_INCIDENT_TYPES)}")
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{severity}'. Must be one of {sorted(VALID_SEVERITIES)}")
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise ValueError(f"Coordinates ({latitude}, {longitude}) are out of valid geographic range.")

        # Match nearest corridor within 5000m
        nearest_seg_id, _ = self.find_nearest_segment(latitude, longitude, max_distance_m=5000.0)

        report_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        now_iso = _utc_now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO incident_reports (
                    report_id, title, description, incident_type, severity,
                    latitude, longitude, district, location_name,
                    reporter_name, reporter_role, contact_number, photo_url,
                    status, associated_segment_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    report_id,
                    title.strip(),
                    description.strip(),
                    incident_type,
                    severity,
                    float(latitude),
                    float(longitude),
                    district.strip(),
                    location_name.strip(),
                    reporter_name.strip(),
                    reporter_role.strip(),
                    contact_number.strip() if contact_number else None,
                    photo_url.strip() if photo_url else None,
                    "pending",  # Always begins as pending!
                    nearest_seg_id,
                    now_iso,
                    now_iso,
                ),
            )

            cursor.execute(
                """
                INSERT INTO accessibility_audit_log (
                    entity_type, entity_id, action, previous_status,
                    new_status, actor, review_notes, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    "incident",
                    report_id,
                    "created",
                    None,
                    "pending",
                    f"{reporter_name} ({reporter_role})",
                    f"New report filed for {incident_type} at {location_name}",
                    now_iso,
                ),
            )
            conn.commit()

        incident = self.get_incident(report_id)
        assert incident is not None
        return incident

    def list_incidents(
        self,
        status: Optional[str] = None,
        incident_type: Optional[str] = None,
        district: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List incident reports with optional filters."""
        query = "SELECT * FROM incident_reports WHERE 1=1"
        params: List[Any] = []
        if status:
            if status not in VALID_INCIDENT_STATUSES:
                raise ValueError(f"Invalid incident status '{status}'. Must be one of {sorted(VALID_INCIDENT_STATUSES)}")
            query += " AND status = ?"
            params.append(status)
        if incident_type:
            if incident_type not in VALID_INCIDENT_TYPES:
                raise ValueError(f"Invalid incident_type '{incident_type}'. Must be one of {sorted(VALID_INCIDENT_TYPES)}")
            query += " AND incident_type = ?"
            params.append(incident_type)
        if district:
            query += " AND district LIKE ?"
            params.append(f"%{district}%")

        query += " ORDER BY created_at DESC;"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_incident(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single incident report by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM incident_reports WHERE report_id = ?;", (report_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def review_incident(
        self,
        report_id: str,
        new_status: str,
        actor: str,
        review_notes: str,
        cascade_to_segment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform an administrative review of a report (e.g. pending -> verified/rejected/resolved).
        Records an audit entry. If cascade_to_segment is provided ('blocked'/'restricted'/'open'),
        it also updates the associated road segment.
        """
        if new_status not in VALID_INCIDENT_STATUSES:
            raise ValueError(f"Invalid new_status '{new_status}'. Allowed: {sorted(VALID_INCIDENT_STATUSES)}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM incident_reports WHERE report_id = ?;", (report_id,))
            row = cursor.fetchone()
            if not row:
                raise KeyError(f"Incident report '{report_id}' not found.")

            prev_status = row["status"]
            associated_seg_id = row["associated_segment_id"]
            now_iso = _utc_now_iso()

            cursor.execute(
                """
                UPDATE incident_reports
                SET status = ?, updated_at = ?
                WHERE report_id = ?;
                """,
                (new_status, now_iso, report_id),
            )

            cursor.execute(
                """
                INSERT INTO accessibility_audit_log (
                    entity_type, entity_id, action, previous_status,
                    new_status, actor, review_notes, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    "incident",
                    report_id,
                    f"reviewed_{new_status}",
                    prev_status,
                    new_status,
                    actor or "Authorized Reviewer",
                    review_notes.strip() if review_notes else f"Report status changed to {new_status}",
                    now_iso,
                ),
            )
            conn.commit()

        # Cascade status to segment if requested and segment exists
        if cascade_to_segment and associated_seg_id:
            if cascade_to_segment in VALID_SEGMENT_STATUSES:
                self.update_segment_status(
                    segment_id=associated_seg_id,
                    new_status=cascade_to_segment,
                    actor=actor,
                    restriction_details=f"Updated via incident {report_id}: {review_notes}",
                    review_notes=f"Cascaded update from incident {report_id}",
                )

        incident = self.get_incident(report_id)
        assert incident is not None
        return incident

    def list_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch audit trail records in reverse chronological order."""
        query = "SELECT * FROM accessibility_audit_log WHERE 1=1"
        params: List[Any] = []
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)

        query += " ORDER BY audit_id DESC LIMIT ?;"
        params.append(max(1, min(limit, 500)))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def save_uploaded_photo(self, filename: str, file_bytes: bytes) -> str:
        """
        Validate and save an uploaded incident photo safely.
        Returns relative URL path (e.g. '/api/accessibility/photos/<safe_name>').
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(
                f"Unsupported image extension '{ext}'. Allowed extensions: {sorted(ALLOWED_IMAGE_EXTENSIONS)}"
            )
        if len(file_bytes) > MAX_PHOTO_SIZE_BYTES:
            raise ValueError(
                f"Photo file size ({len(file_bytes)} bytes) exceeds the 5 MB maximum limit."
            )

        safe_filename = f"incident_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        target_path = UPLOADS_DIR / safe_filename
        with open(target_path, "wb") as f:
            f.write(file_bytes)

        return f"/api/accessibility/photos/{safe_filename}"

    def check_route_against_accessibility(
        self, route_coords: List[Tuple[float, float]], buffer_distance_m: float = 800.0
    ) -> Dict[str, Any]:
        """
        Check whether a candidate route polyline intersects any verified blocked or restricted corridors.
        Returns accessibility impact details and score penalty.
        """
        segments = self.list_segments()
        impacted_segments = []
        is_blocked = False
        penalty = 0.0

        # Sample route points (up to 30 sample points)
        sample_step = max(1, len(route_coords) // 30)
        sampled_route = route_coords[::sample_step]

        for seg in segments:
            if seg["status"] == "open":
                continue

            seg_coords = seg["coordinates"]
            intersected = False
            for r_lat, r_lng in sampled_route:
                for i in range(len(seg_coords) - 1):
                    a_lat, a_lng = seg_coords[i]
                    b_lat, b_lng = seg_coords[i + 1]
                    dist = _distance_point_to_segment_m(r_lat, r_lng, a_lat, a_lng, b_lat, b_lng)
                    if dist <= buffer_distance_m:
                        intersected = True
                        break
                if intersected:
                    break

            if intersected:
                impacted_segments.append(
                    {
                        "segment_id": seg["segment_id"],
                        "name": seg["name"],
                        "status": seg["status"],
                        "district": seg["district"],
                        "restriction_details": seg["restriction_details"],
                    }
                )
                if seg["status"] == "blocked":
                    is_blocked = True
                    penalty += 45.0
                elif seg["status"] == "restricted":
                    penalty += 20.0

        score = max(0.0, 100.0 - penalty)
        return {
            "accessibility_score": round(score, 1),
            "is_blocked": is_blocked,
            "impacted_segments_count": len(impacted_segments),
            "impacted_segments": impacted_segments,
        }
