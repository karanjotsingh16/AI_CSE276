"""GPS Vehicle and Delivery Tracking Service (Module F).

Implements Module F (GPS Vehicle and Delivery Tracking) for the NER SmartRoute platform.

Features:
- Vehicle registration & fleet status management (4x4, Van, Heavy Truck, etc.).
- Delivery lifecycle: scheduled, dispatched, in_transit, delayed, delivered, interrupted.
- Secure telemetry location update API with speed, bearing, and timestamp.
- Route deviation detection (flags deviations exceeding 500 meters from planned geometry).
- Estimated Time of Arrival (ETA) tracking based on static travel-time routing estimates.
- Clearly labeled Demonstration GPS Simulation Mode with synthetic progression and deviation testing.

Academic Integrity & Operating Rules:
- Never fabricate live vehicle locations.
- Live telemetry is accepted only via explicit telemetry updates.
- Simulated telemetry is strictly labeled:
  'DEMONSTRATION MODE — SIMULATED GPS TELEMETRY, NOT LIVE VEHICLE SATELLITE TRACKING.'
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BACKEND_DIR = (
    Path(__file__).resolve().parent.parent
    if Path(__file__).resolve().parent.name in ("core", "services", "scripts", "tests")
    else Path(__file__).resolve().parent
)
DATA_DIR = BACKEND_DIR / "data"
DEFAULT_TRACKING_DB_PATH = DATA_DIR / "tracking.db"

VALID_VEHICLE_TYPES = {"4x4", "Van", "Heavy Truck", "Electric Van", "Pickup"}
VALID_DELIVERY_STATUSES = {
    "scheduled",
    "dispatched",
    "in_transit",
    "delayed",
    "delivered",
    "interrupted",
}
VALID_GOODS_CATEGORIES = {
    "Medical Supplies",
    "Food Supplies",
    "Relief Materials",
    "General Cargo",
    "Vaccines / Cold Chain",
}
VALID_PRIORITIES = {"Emergency", "High", "Normal", "Low"}
VALID_TELEMETRY_MODES = {"real_gps", "simulated_demo"}

ROUTE_DEVIATION_THRESHOLD_M = 500.0  # 500 meters threshold to flag deviation


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
    d_ab = _haversine_distance_m(a_lat, a_lng, b_lat, b_lng)
    if d_ab < 1e-6:
        return _haversine_distance_m(p_lat, p_lng, a_lat, a_lng)

    cos_lat = math.cos(math.radians((a_lat + b_lat) / 2.0))
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


def _calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    deg = math.degrees(math.atan2(y, x))
    return (deg + 360.0) % 360.0


# Initial baseline fleet operating across Meghalaya and NER corridors
SEED_VEHICLES = [
    {
        "vehicle_id": "ML-05-TR-1042",
        "name": "Meghalaya Relief 4x4 Unit Alpha",
        "vehicle_type": "4x4",
        "capacity_kg": 1200.0,
        "assigned_driver_name": "Bah K. Marbaniang",
        "assigned_driver_contact": "+91 98620 11421",
        "current_latitude": 25.5788,
        "current_longitude": 91.8933,
        "current_speed_kph": 32.5,
        "current_bearing": 175.0,
        "telemetry_mode": "simulated_demo",
    },
    {
        "vehicle_id": "ML-01-HV-4401",
        "name": "Civil Supplies Heavy Freight #1",
        "vehicle_type": "Heavy Truck",
        "capacity_kg": 9500.0,
        "assigned_driver_name": "D. Sangma",
        "assigned_driver_contact": "+91 94361 88302",
        "current_latitude": 25.5650,
        "current_longitude": 91.6400,
        "current_speed_kph": 28.0,
        "current_bearing": 270.0,
        "telemetry_mode": "simulated_demo",
    },
    {
        "vehicle_id": "AS-01-EV-2091",
        "name": "Guwahati-Shillong EV Courier",
        "vehicle_type": "Electric Van",
        "capacity_kg": 850.0,
        "assigned_driver_name": "B. Barman",
        "assigned_driver_contact": "+91 98540 77123",
        "current_latitude": 25.6601,
        "current_longitude": 91.8980,
        "current_speed_kph": 45.0,
        "current_bearing": 180.0,
        "telemetry_mode": "simulated_demo",
    },
    {
        "vehicle_id": "ML-08-VN-3312",
        "name": "East Khasi Emergency Medical Van",
        "vehicle_type": "Van",
        "capacity_kg": 1500.0,
        "assigned_driver_name": "S. Nongrum",
        "assigned_driver_contact": "+91 97740 55219",
        "current_latitude": 25.4200,
        "current_longitude": 91.7800,
        "current_speed_kph": 38.0,
        "current_bearing": 195.0,
        "telemetry_mode": "simulated_demo",
    },
]


class TrackingService:
    """Manages vehicle registration, delivery dispatching, live telemetry, and demonstration simulation."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_TRACKING_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_database(self) -> None:
        """Create schema and seed baseline fleet if not already present."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vehicles (
                    vehicle_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    vehicle_type TEXT NOT NULL,
                    capacity_kg REAL NOT NULL,
                    assigned_driver_name TEXT NOT NULL,
                    assigned_driver_contact TEXT,
                    current_latitude REAL,
                    current_longitude REAL,
                    current_speed_kph REAL DEFAULT 0.0,
                    current_bearing REAL DEFAULT 0.0,
                    last_telemetry_at TEXT,
                    telemetry_mode TEXT DEFAULT 'simulated_demo',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deliveries (
                    delivery_id TEXT PRIMARY KEY,
                    vehicle_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    goods_category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    origin_name TEXT NOT NULL,
                    origin_lat REAL NOT NULL,
                    origin_lng REAL NOT NULL,
                    destination_name TEXT NOT NULL,
                    destination_lat REAL NOT NULL,
                    destination_lng REAL NOT NULL,
                    dispatch_time TEXT,
                    estimated_arrival_time TEXT,
                    actual_arrival_time TEXT,
                    status TEXT NOT NULL CHECK(status IN ('scheduled', 'dispatched', 'in_transit', 'delayed', 'delivered', 'interrupted')),
                    planned_distance_km REAL NOT NULL,
                    planned_duration_minutes REAL NOT NULL,
                    planned_route_geometry TEXT NOT NULL,
                    progress_pct REAL DEFAULT 0.0,
                    is_deviated INTEGER DEFAULT 0,
                    deviation_distance_m REAL DEFAULT 0.0,
                    delay_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT NOT NULL,
                    delivery_id TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    speed_kph REAL NOT NULL,
                    bearing REAL NOT NULL,
                    telemetry_source TEXT NOT NULL,
                    deviation_distance_m REAL DEFAULT 0.0,
                    timestamp TEXT NOT NULL
                );
                """
            )

            # Seed initial vehicles if empty
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vehicles;")
            count = cursor.fetchone()[0]
            now_iso = _utc_now_iso()
            if count == 0:
                for v in SEED_VEHICLES:
                    cursor.execute(
                        """
                        INSERT INTO vehicles (
                            vehicle_id, name, vehicle_type, capacity_kg,
                            assigned_driver_name, assigned_driver_contact,
                            current_latitude, current_longitude, current_speed_kph,
                            current_bearing, last_telemetry_at, telemetry_mode,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            v["vehicle_id"],
                            v["name"],
                            v["vehicle_type"],
                            v["capacity_kg"],
                            v["assigned_driver_name"],
                            v["assigned_driver_contact"],
                            v["current_latitude"],
                            v["current_longitude"],
                            v["current_speed_kph"],
                            v["current_bearing"],
                            now_iso,
                            v["telemetry_mode"],
                            now_iso,
                            now_iso,
                        ),
                    )

                # Seed 2 realistic active demonstration deliveries
                shillong_to_sohra_coords = [
                    [25.5788, 91.8933],
                    [25.5100, 91.8500],
                    [25.4200, 91.7800],
                    [25.2800, 91.7300],
                ]
                shillong_to_mairang_coords = [
                    [25.5788, 91.8933],
                    [25.5600, 91.7500],
                    [25.5650, 91.6400],
                ]

                dispatch_iso = (datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat()
                eta_iso = (datetime.now(timezone.utc) + timedelta(minutes=45)).isoformat()

                cursor.execute(
                    """
                    INSERT INTO deliveries (
                        delivery_id, vehicle_id, title, goods_category, priority,
                        origin_name, origin_lat, origin_lng, destination_name, destination_lat, destination_lng,
                        dispatch_time, estimated_arrival_time, status, planned_distance_km,
                        planned_duration_minutes, planned_route_geometry, progress_pct,
                        is_deviated, deviation_distance_m, delay_reason, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        "DEL-20261030-SOHRA01",
                        "ML-05-TR-1042",
                        "Urgent Medical & Vaccine Dispatch to Sohra CHC",
                        "Medical Supplies",
                        "Emergency",
                        "Shillong Civil Hospital",
                        25.5788,
                        91.8933,
                        "Sohra Community Health Centre",
                        25.2800,
                        91.7300,
                        dispatch_iso,
                        eta_iso,
                        "in_transit",
                        54.2,
                        70.0,
                        json.dumps(shillong_to_sohra_coords),
                        35.0,
                        0,
                        45.0,
                        None,
                        now_iso,
                        now_iso,
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO deliveries (
                        delivery_id, vehicle_id, title, goods_category, priority,
                        origin_name, origin_lat, origin_lng, destination_name, destination_lat, destination_lng,
                        dispatch_time, estimated_arrival_time, status, planned_distance_km,
                        planned_duration_minutes, planned_route_geometry, progress_pct,
                        is_deviated, deviation_distance_m, delay_reason, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        "DEL-20261030-MAIRANG02",
                        "ML-01-HV-4401",
                        "Essential Grains & Ration Supply to Mairang Block",
                        "Food Supplies",
                        "High",
                        "Shillong FCI Godown",
                        25.5788,
                        91.8933,
                        "Mairang Sub-Divisional Depot",
                        25.5650,
                        91.6400,
                        dispatch_iso,
                        eta_iso,
                        "in_transit",
                        42.8,
                        60.0,
                        json.dumps(shillong_to_mairang_coords),
                        60.0,
                        0,
                        30.0,
                        None,
                        now_iso,
                        now_iso,
                    ),
                )

            conn.commit()

    def register_vehicle(
        self,
        vehicle_id: str,
        name: str,
        vehicle_type: str,
        capacity_kg: float,
        assigned_driver_name: str,
        assigned_driver_contact: Optional[str] = None,
        initial_lat: Optional[float] = None,
        initial_lng: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new logistics vehicle in the fleet catalog."""
        v_id = vehicle_id.strip().upper()
        if vehicle_type not in VALID_VEHICLE_TYPES:
            raise ValueError(f"Invalid vehicle_type '{vehicle_type}'. Must be one of {sorted(VALID_VEHICLE_TYPES)}")
        if capacity_kg <= 0:
            raise ValueError("capacity_kg must be greater than zero.")

        now_iso = _utc_now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vehicle_id FROM vehicles WHERE vehicle_id = ?;", (v_id,))
            if cursor.fetchone():
                raise ValueError(f"Vehicle '{v_id}' is already registered.")

            cursor.execute(
                """
                INSERT INTO vehicles (
                    vehicle_id, name, vehicle_type, capacity_kg,
                    assigned_driver_name, assigned_driver_contact,
                    current_latitude, current_longitude, current_speed_kph,
                    current_bearing, last_telemetry_at, telemetry_mode,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    v_id,
                    name.strip(),
                    vehicle_type,
                    float(capacity_kg),
                    assigned_driver_name.strip(),
                    assigned_driver_contact.strip() if assigned_driver_contact else None,
                    float(initial_lat) if initial_lat is not None else None,
                    float(initial_lng) if initial_lng is not None else None,
                    0.0,
                    0.0,
                    now_iso if initial_lat is not None else None,
                    "simulated_demo",
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()

        vehicle = self.get_vehicle(v_id)
        assert vehicle is not None
        return vehicle

    def list_vehicles(self, vehicle_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List registered vehicles with optional vehicle_type filter."""
        query = "SELECT * FROM vehicles WHERE 1=1"
        params: List[Any] = []
        if vehicle_type:
            if vehicle_type not in VALID_VEHICLE_TYPES:
                raise ValueError(f"Invalid vehicle_type '{vehicle_type}'.")
            query += " AND vehicle_type = ?"
            params.append(vehicle_type)

        query += " ORDER BY vehicle_id ASC;"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def get_vehicle(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details of a single vehicle."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vehicles WHERE vehicle_id = ?;", (vehicle_id.strip().upper(),))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def create_delivery(
        self,
        vehicle_id: str,
        title: str,
        goods_category: str,
        priority: str,
        origin_name: str,
        origin_lat: float,
        origin_lng: float,
        destination_name: str,
        destination_lat: float,
        destination_lng: float,
        planned_distance_km: float,
        planned_duration_minutes: float,
        planned_route_geometry: List[Tuple[float, float]],
        dispatch_immediately: bool = True,
    ) -> Dict[str, Any]:
        """Create and dispatch a new delivery mission."""
        v_id = vehicle_id.strip().upper()
        if not self.get_vehicle(v_id):
            raise KeyError(f"Vehicle '{v_id}' not found in registry.")
        if goods_category not in VALID_GOODS_CATEGORIES:
            raise ValueError(f"Invalid goods_category '{goods_category}'. Must be one of {sorted(VALID_GOODS_CATEGORIES)}")
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{priority}'. Must be one of {sorted(VALID_PRIORITIES)}")
        if not planned_route_geometry or len(planned_route_geometry) < 2:
            raise ValueError("planned_route_geometry must have at least 2 coordinate points.")

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        dispatch_iso = now_iso if dispatch_immediately else None
        eta = now + timedelta(minutes=planned_duration_minutes)
        eta_iso = eta.isoformat()
        initial_status = "in_transit" if dispatch_immediately else "scheduled"

        delivery_id = f"DEL-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO deliveries (
                    delivery_id, vehicle_id, title, goods_category, priority,
                    origin_name, origin_lat, origin_lng, destination_name, destination_lat, destination_lng,
                    dispatch_time, estimated_arrival_time, status, planned_distance_km,
                    planned_duration_minutes, planned_route_geometry, progress_pct,
                    is_deviated, deviation_distance_m, delay_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    delivery_id,
                    v_id,
                    title.strip(),
                    goods_category,
                    priority,
                    origin_name.strip(),
                    float(origin_lat),
                    float(origin_lng),
                    destination_name.strip(),
                    float(destination_lat),
                    float(destination_lng),
                    dispatch_iso,
                    eta_iso,
                    initial_status,
                    float(planned_distance_km),
                    float(planned_duration_minutes),
                    json.dumps(planned_route_geometry),
                    0.0,
                    0,
                    0.0,
                    None,
                    now_iso,
                    now_iso,
                ),
            )

            # Update vehicle location to origin
            cursor.execute(
                """
                UPDATE vehicles
                SET current_latitude = ?, current_longitude = ?, last_telemetry_at = ?, updated_at = ?
                WHERE vehicle_id = ?;
                """,
                (float(origin_lat), float(origin_lng), now_iso, now_iso, v_id),
            )
            conn.commit()

        delivery = self.get_delivery(delivery_id)
        assert delivery is not None
        return delivery

    def list_deliveries(
        self, status: Optional[str] = None, vehicle_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List deliveries with optional status or vehicle filter."""
        query = "SELECT * FROM deliveries WHERE 1=1"
        params: List[Any] = []
        if status:
            if status not in VALID_DELIVERY_STATUSES:
                raise ValueError(f"Invalid delivery status '{status}'. Must be one of {sorted(VALID_DELIVERY_STATUSES)}")
            query += " AND status = ?"
            params.append(status)
        if vehicle_id:
            query += " AND vehicle_id = ?"
            params.append(vehicle_id.strip().upper())

        query += " ORDER BY created_at DESC;"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["planned_route_geometry"] = json.loads(d.pop("planned_route_geometry"))
                d["is_deviated"] = bool(d["is_deviated"])
                results.append(d)
            return results

    def get_delivery(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details of a single delivery."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deliveries WHERE delivery_id = ?;", (delivery_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["planned_route_geometry"] = json.loads(d.pop("planned_route_geometry"))
            d["is_deviated"] = bool(d["is_deviated"])
            return d

    def update_delivery_status(
        self, delivery_id: str, new_status: str, delay_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update delivery operational status."""
        if new_status not in VALID_DELIVERY_STATUSES:
            raise ValueError(f"Invalid new_status '{new_status}'. Must be one of {sorted(VALID_DELIVERY_STATUSES)}")

        now_iso = _utc_now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT delivery_id, status FROM deliveries WHERE delivery_id = ?;", (delivery_id,))
            row = cursor.fetchone()
            if not row:
                raise KeyError(f"Delivery '{delivery_id}' not found.")

            actual_arrival = now_iso if new_status == "delivered" else None

            cursor.execute(
                """
                UPDATE deliveries
                SET status = ?, delay_reason = ?, actual_arrival_time = COALESCE(?, actual_arrival_time), updated_at = ?
                WHERE delivery_id = ?;
                """,
                (new_status, delay_reason.strip() if delay_reason else None, actual_arrival, now_iso, delivery_id),
            )
            conn.commit()

        delivery = self.get_delivery(delivery_id)
        assert delivery is not None
        return delivery

    def record_telemetry(
        self,
        vehicle_id: str,
        latitude: float,
        longitude: float,
        speed_kph: float = 0.0,
        bearing: float = 0.0,
        delivery_id: Optional[str] = None,
        source: str = "real_gps",
    ) -> Dict[str, Any]:
        """
        Record real or simulated telemetry location for a vehicle.
        Checks for route deviation against active delivery geometry.
        """
        v_id = vehicle_id.strip().upper()
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise ValueError(f"Coordinates ({latitude}, {longitude}) out of range.")
        if source not in VALID_TELEMETRY_MODES:
            raise ValueError(f"Invalid source '{source}'. Must be 'real_gps' or 'simulated_demo'.")

        vehicle = self.get_vehicle(v_id)
        if not vehicle:
            raise KeyError(f"Vehicle '{v_id}' not registered.")

        # Determine active delivery if not provided
        active_delivery = None
        if delivery_id:
            active_delivery = self.get_delivery(delivery_id)
        else:
            deliveries = self.list_deliveries(vehicle_id=v_id)
            for d in deliveries:
                if d["status"] in ("in_transit", "delayed", "dispatched"):
                    active_delivery = d
                    break

        deviation_m = 0.0
        is_deviated = False
        progress_pct = 0.0

        if active_delivery and active_delivery.get("planned_route_geometry"):
            coords = active_delivery["planned_route_geometry"]
            # Find closest distance to polyline
            min_dist = float("inf")
            closest_idx = 0
            for i in range(len(coords) - 1):
                a_lat, a_lng = coords[i]
                b_lat, b_lng = coords[i + 1]
                dist = _distance_point_to_segment_m(latitude, longitude, a_lat, a_lng, b_lat, b_lng)
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i

            deviation_m = round(min_dist, 1)
            is_deviated = deviation_m > ROUTE_DEVIATION_THRESHOLD_M

            # Estimate progress along route segments
            total_pts = len(coords)
            if total_pts > 1:
                progress_pct = round(min(100.0, (closest_idx / (total_pts - 1)) * 100.0), 1)

        now_iso = _utc_now_iso()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Update vehicle state
            cursor.execute(
                """
                UPDATE vehicles
                SET current_latitude = ?, current_longitude = ?, current_speed_kph = ?,
                    current_bearing = ?, last_telemetry_at = ?, telemetry_mode = ?, updated_at = ?
                WHERE vehicle_id = ?;
                """,
                (
                    float(latitude),
                    float(longitude),
                    max(0.0, float(speed_kph)),
                    float(bearing) % 360.0,
                    now_iso,
                    source,
                    now_iso,
                    v_id,
                ),
            )

            # Update active delivery progress & deviation if present
            if active_delivery:
                del_id = active_delivery["delivery_id"]
                cursor.execute(
                    """
                    UPDATE deliveries
                    SET progress_pct = MAX(progress_pct, ?),
                        is_deviated = ?,
                        deviation_distance_m = ?,
                        updated_at = ?
                    WHERE delivery_id = ?;
                    """,
                    (progress_pct, 1 if is_deviated else 0, deviation_m, now_iso, del_id),
                )

            # Insert into telemetry logs
            cursor.execute(
                """
                INSERT INTO telemetry_logs (
                    vehicle_id, delivery_id, latitude, longitude, speed_kph,
                    bearing, telemetry_source, deviation_distance_m, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    v_id,
                    active_delivery["delivery_id"] if active_delivery else None,
                    float(latitude),
                    float(longitude),
                    float(speed_kph),
                    float(bearing),
                    source,
                    deviation_m,
                    now_iso,
                ),
            )
            conn.commit()

        updated_vehicle = self.get_vehicle(v_id)
        assert updated_vehicle is not None
        return {
            "vehicle": updated_vehicle,
            "telemetry": {
                "latitude": latitude,
                "longitude": longitude,
                "speed_kph": speed_kph,
                "bearing": bearing,
                "telemetry_source": source,
                "timestamp": now_iso,
            },
            "delivery_id": active_delivery["delivery_id"] if active_delivery else None,
            "is_deviated": is_deviated,
            "deviation_distance_m": deviation_m,
            "progress_pct": progress_pct,
            "disclaimer": (
                "DEMONSTRATION MODE — SIMULATED GPS TELEMETRY, NOT LIVE VEHICLE SATELLITE TRACKING."
                if source == "simulated_demo"
                else "AUTHENTIC GPS TELEMETRY RECORDED."
            ),
        }

    def step_simulated_telemetry(
        self, delivery_id: str, progress_step_pct: float = 5.0, simulate_deviation: bool = False
    ) -> Dict[str, Any]:
        """
        Advance a delivery vehicle along its planned geometry for demonstration purposes.
        If simulate_deviation is True, injects an offset to demonstrate route deviation detection.
        """
        delivery = self.get_delivery(delivery_id)
        if not delivery:
            raise KeyError(f"Delivery '{delivery_id}' not found.")

        coords = delivery["planned_route_geometry"]
        if len(coords) < 2:
            raise ValueError("Delivery has insufficient route geometry.")

        current_pct = delivery["progress_pct"]
        new_pct = min(100.0, current_pct + progress_step_pct)

        # Interpolate position along polyline
        target_idx_float = (new_pct / 100.0) * (len(coords) - 1)
        base_idx = int(target_idx_float)
        frac = target_idx_float - base_idx

        if base_idx >= len(coords) - 1:
            lat, lng = coords[-1]
            bearing = 0.0
        else:
            p1 = coords[base_idx]
            p2 = coords[base_idx + 1]
            lat = p1[0] + (p2[0] - p1[0]) * frac
            lng = p1[1] + (p2[1] - p1[1]) * frac
            bearing = _calculate_bearing_deg(p1[0], p1[1], p2[0], p2[1])

        # If user asks to test deviation detection, displace coordinates by ~800m
        if simulate_deviation:
            lat += 0.007  # ~770m latitude shift
            lng += 0.005  # ~500m longitude shift

        # Auto-complete status if reached 100%
        if new_pct >= 100.0 and not simulate_deviation:
            self.update_delivery_status(delivery_id, "delivered")

        speed_kph = 35.0 if not simulate_deviation else 15.0

        return self.record_telemetry(
            vehicle_id=delivery["vehicle_id"],
            latitude=lat,
            longitude=lng,
            speed_kph=speed_kph,
            bearing=bearing,
            delivery_id=delivery_id,
            source="simulated_demo",
        )

    def get_telemetry_history(
        self, vehicle_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch recent telemetry logs for a vehicle."""
        v_id = vehicle_id.strip().upper()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM telemetry_logs
                WHERE vehicle_id = ?
                ORDER BY log_id DESC
                LIMIT ?;
                """,
                (v_id, max(1, min(limit, 200))),
            )
            return [dict(r) for r in cursor.fetchall()]

