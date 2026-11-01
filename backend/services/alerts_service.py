"""Alerts & Notifications System Service (Module G).

Implements Module G (Alerts and Notifications) for the NER SmartRoute platform.

Features:
- In-app notification center with read/unread tracking.
- Severity tiering: info, warning, severe, critical.
- Multi-domain automated triggers:
  * Verified road closures & restrictions (AccessibilityService)
  * Confirmed landslides & flash floods (AccessibilityService)
  * Official severe weather warnings (Open-Meteo / IMD)
  * Logistics vehicle route deviations & transit delays (TrackingService)
  * Regional highway advisory disruptions (DisruptionsService)
- Deduplication engine: Prevents duplicate alert spam via deterministic compound keys.
- Channel abstraction: Live active 'in_app' channel, plus registered extensible adapters
  (SMS, Email, Webhook) with honest configuration status reporting.

Academic Integrity & Operating Rules:
- Never claim notifications are delivered through channels that are not configured.
- Deduplicate alerts deterministically to prevent duplicate spam.
"""

from __future__ import annotations

import hashlib
import json
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
DEFAULT_ALERTS_DB_PATH = DATA_DIR / "alerts.db"

VALID_SEVERITIES = {"info", "warning", "severe", "critical"}
VALID_CATEGORIES = {
    "road_closure",
    "landslide",
    "flood",
    "severe_weather",
    "vehicle_delay",
    "route_disruption",
    "route_deviation",
}
VALID_CHANNELS = {"in_app", "sms_adapter", "email_adapter", "push_webhook"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_dedup_key(category: str, entity_id: str, date_bucket: str) -> str:
    raw = f"{category}:{entity_id}:{date_bucket}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


# Initial verified regional alerts
SEED_ALERTS = [
    {
        "alert_id": "ALT-20261030-001",
        "dedup_key": "seed_umiam_bridge_load_limit",
        "title": "Umiam Dam Bridge Single-Lane Load Limit (10T)",
        "message": "Meghalaya PWD & NHIDCL: Heavy freight (>10T) must divert via Shillong Eastern Bypass (Umsning-Mawryngkneng). Single-lane controlled movement.",
        "category": "route_disruption",
        "severity": "warning",
        "source": "Meghalaya PWD / NHIDCL Advisory",
        "latitude": 25.6601,
        "longitude": 91.8980,
        "radius_km": 10.0,
        "district": "Ri-Bhoi",
        "entity_id": "ADV-MEG-2026-002",
        "is_read": 0,
        "channel": "in_app",
    },
    {
        "alert_id": "ALT-20261030-002",
        "dedup_key": "seed_sonapur_debris_clearance",
        "title": "NH-6 Sonapur Tunnel Approach Hill-Cutting",
        "message": "NHIDCL: Debris clearance active on outer lane. Heavy rain creates periodic slope instability. Traffic regulated under convoy control.",
        "category": "landslide",
        "severity": "severe",
        "source": "NHIDCL Field Office Jowai",
        "latitude": 25.0700,
        "longitude": 92.3800,
        "radius_km": 15.0,
        "district": "East Jaintia Hills",
        "entity_id": "ADV-MEG-2026-001",
        "is_read": 0,
        "channel": "in_app",
    },
    {
        "alert_id": "ALT-20261030-003",
        "dedup_key": "seed_cherra_dense_fog_warning",
        "title": "Dense Valley Fog & Reduced Visibility on SH-5",
        "message": "Open-Meteo & IMD Observation: Visibility below 150m between Mawphlang and Sohra. Mountain transport advised to maintain low speeds.",
        "category": "severe_weather",
        "severity": "info",
        "source": "Open-Meteo Regional Weather Model",
        "latitude": 25.2800,
        "longitude": 91.7300,
        "radius_km": 20.0,
        "district": "East Khasi Hills",
        "entity_id": "WX-MEG-20261030-SOHRA",
        "is_read": 0,
        "channel": "in_app",
    },
]


class AlertsService:
    """Manages notifications, alert generation, deduplication, and read states."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_ALERTS_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Create schema and insert baseline seed alerts if empty."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    dedup_key TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('road_closure', 'landslide', 'flood', 'severe_weather', 'vehicle_delay', 'route_disruption', 'route_deviation')),
                    severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'severe', 'critical')),
                    source TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    radius_km REAL DEFAULT 15.0,
                    district TEXT,
                    entity_id TEXT,
                    is_read INTEGER DEFAULT 0,
                    channel TEXT DEFAULT 'in_app',
                    created_at TEXT NOT NULL
                );
                """
            )
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts;")
            count = cursor.fetchone()[0]
            if count == 0:
                now_iso = _utc_now_iso()
                for a in SEED_ALERTS:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO alerts (
                            alert_id, dedup_key, title, message, category,
                            severity, source, latitude, longitude, radius_km,
                            district, entity_id, is_read, channel, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            a["alert_id"],
                            a["dedup_key"],
                            a["title"],
                            a["message"],
                            a["category"],
                            a["severity"],
                            a["source"],
                            a["latitude"],
                            a["longitude"],
                            a["radius_km"],
                            a["district"],
                            a["entity_id"],
                            a["is_read"],
                            a["channel"],
                            now_iso,
                        ),
                    )
            conn.commit()

    def create_alert(
        self,
        title: str,
        message: str,
        category: str,
        severity: str,
        source: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 15.0,
        district: Optional[str] = None,
        entity_id: Optional[str] = None,
        channel: str = "in_app",
        custom_dedup_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new alert if it does not already exist.
        Deduplicates against category, entity_id, and current date.
        Returns the alert dict if inserted, or None if deduplicated.
        """
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of {sorted(VALID_CATEGORIES)}")
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{severity}'. Must be one of {sorted(VALID_SEVERITIES)}")

        now = datetime.now(timezone.utc)
        date_bucket = now.strftime("%Y-%m-%d")
        effective_entity = entity_id or title
        dedup_key = custom_dedup_key or _generate_dedup_key(category, effective_entity, date_bucket)

        alert_id = f"ALT-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        now_iso = now.isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check existing
            cursor.execute("SELECT alert_id FROM alerts WHERE dedup_key = ?;", (dedup_key,))
            if cursor.fetchone():
                return None  # Duplicate detected, ignore cleanly

            cursor.execute(
                """
                INSERT INTO alerts (
                    alert_id, dedup_key, title, message, category,
                    severity, source, latitude, longitude, radius_km,
                    district, entity_id, is_read, channel, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
                """,
                (
                    alert_id,
                    dedup_key,
                    title.strip(),
                    message.strip(),
                    category,
                    severity,
                    source.strip(),
                    float(latitude) if latitude is not None else None,
                    float(longitude) if longitude is not None else None,
                    float(radius_km),
                    district.strip() if district else None,
                    entity_id.strip() if entity_id else None,
                    channel,
                    now_iso,
                ),
            )
            conn.commit()

        return self.get_alert(alert_id)

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details of a single alert."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts WHERE alert_id = ?;", (alert_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["is_read"] = bool(d["is_read"])
            return d

    def list_alerts(
        self,
        unread_only: bool = False,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List alerts ordered by reverse chronological order."""
        query = "SELECT * FROM alerts WHERE 1=1"
        params: List[Any] = []
        if unread_only:
            query += " AND is_read = 0"
        if category:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"Invalid category '{category}'.")
            query += " AND category = ?"
            params.append(category)
        if severity:
            if severity not in VALID_SEVERITIES:
                raise ValueError(f"Invalid severity '{severity}'.")
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(max(1, min(limit, 200)))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = []
            for r in cursor.fetchall():
                d = dict(r)
                d["is_read"] = bool(d["is_read"])
                results.append(d)
            return results

    def mark_alert_read(self, alert_id: str, is_read: bool = True) -> Dict[str, Any]:
        """Mark an alert as read or unread."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT alert_id FROM alerts WHERE alert_id = ?;", (alert_id,))
            if not cursor.fetchone():
                raise KeyError(f"Alert '{alert_id}' not found.")

            cursor.execute(
                "UPDATE alerts SET is_read = ? WHERE alert_id = ?;",
                (1 if is_read else 0, alert_id),
            )
            conn.commit()

        updated = self.get_alert(alert_id)
        assert updated is not None
        return updated

    def mark_all_read(self) -> int:
        """Mark all unread alerts as read."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE alerts SET is_read = 1 WHERE is_read = 0;")
            conn.commit()
            return cursor.rowcount

    def get_unread_count(self) -> int:
        """Return the number of unread alerts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_read = 0;")
            return cursor.fetchone()[0]

    def sync_automated_triggers(
        self,
        accessibility_svc: Optional[Any] = None,
        disruptions_svc: Optional[Any] = None,
        tracking_svc: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate live state from other modules and generate deduplicated alerts.
        Deduplication keys guarantee zero duplicate spam.
        """
        created_alerts = []

        # 1. From Accessibility Service: check blocked road corridors & verified incidents
        if accessibility_svc:
            try:
                segments = accessibility_svc.list_segments()
                for seg in segments:
                    if seg["status"] == "blocked":
                        lat = seg["coordinates"][0][0] if seg["coordinates"] else 25.5788
                        lng = seg["coordinates"][0][1] if seg["coordinates"] else 91.8933
                        alt = self.create_alert(
                            title=f"Road Closure: {seg['name']}",
                            message=f"Corridor is fully blocked. {seg.get('restriction_details') or 'Traffic suspended by authorities.'}",
                            category="road_closure",
                            severity="critical",
                            source="PWD / District Disaster Authority",
                            latitude=lat,
                            longitude=lng,
                            district=seg.get("district"),
                            entity_id=seg["segment_id"],
                        )
                        if alt:
                            created_alerts.append(alt)

                incidents = accessibility_svc.list_incidents(status="verified")
                for inc in incidents:
                    if inc["severity"] in ("severe", "critical"):
                        category = "landslide" if inc["incident_type"] == "landslide" else "flood" if inc["incident_type"] == "flood" else "route_disruption"
                        alt = self.create_alert(
                            title=f"Verified {inc['incident_type'].replace('_', ' ').title()}: {inc['location_name']}",
                            message=f"{inc['description']} (Severity: {inc['severity'].upper()})",
                            category=category,
                            severity=inc["severity"],
                            source="Verified Field Patrol Report",
                            latitude=inc["latitude"],
                            longitude=inc["longitude"],
                            district=inc.get("district"),
                            entity_id=inc["report_id"],
                        )
                        if alt:
                            created_alerts.append(alt)
            except Exception as e:
                print(f"AlertsService: error syncing accessibility triggers: {e}")

        # 2. From Disruptions Service: check active advisories
        if disruptions_svc:
            try:
                disruptions = disruptions_svc.list_active_disruptions()
                for d in disruptions:
                    d_id = d.get("id") or d.get("advisory_id") or "adv"
                    d_title = d.get("title", "Regional Disruption")
                    d_agency = d.get("issuing_agency") or d.get("authority") or "Regional Highway Authority"
                    d_desc = d.get("description", "")
                    d_lat = d.get("latitude") if "latitude" in d else d.get("lat")
                    d_lng = d.get("longitude") if "longitude" in d else d.get("lng")
                    radius_km = (d.get("radius_m", 1500.0) / 1000.0) if "radius_m" in d else d.get("radius_km", 1.5)
                    raw_sev = str(d.get("severity", "warning")).lower()
                    sev = "severe" if raw_sev in ("critical", "severe") else "warning" if raw_sev in ("warning", "advisory") else "info"

                    alt = self.create_alert(
                        title=f"Regional Advisory: {d_title}",
                        message=d_desc,
                        category="route_disruption",
                        severity=sev,
                        source=d_agency,
                        latitude=d_lat,
                        longitude=d_lng,
                        radius_km=radius_km,
                        entity_id=d_id,
                    )
                    if alt:
                        created_alerts.append(alt)
            except Exception as e:
                print(f"AlertsService: error syncing disruption triggers: {e}")

        # 3. From Tracking Service: check deviated deliveries & vehicle delays
        if tracking_svc:
            try:
                deliveries = tracking_svc.list_deliveries()
                for deliv in deliveries:
                    if deliv["is_deviated"]:
                        alt = self.create_alert(
                            title=f"Route Deviation: Vehicle {deliv['vehicle_id']}",
                            message=f"Mission '{deliv['title']}' is {deliv['deviation_distance_m']:.0f}m off planned route corridor.",
                            category="route_deviation",
                            severity="warning",
                            source="GPS Telemetry Deviation Engine",
                            latitude=deliv["origin_lat"],
                            longitude=deliv["origin_lng"],
                            entity_id=f"dev_{deliv['delivery_id']}",
                        )
                        if alt:
                            created_alerts.append(alt)
                    elif deliv["status"] == "delayed":
                        alt = self.create_alert(
                            title=f"Delivery Delayed: {deliv['title']}",
                            message=f"Reason: {deliv.get('delay_reason') or 'Encountered corridor delay.'}",
                            category="vehicle_delay",
                            severity="warning",
                            source="Fleet Dispatch Controller",
                            entity_id=f"delay_{deliv['delivery_id']}",
                        )
                        if alt:
                            created_alerts.append(alt)
            except Exception as e:
                print(f"AlertsService: error syncing tracking triggers: {e}")

        return {
            "created_count": len(created_alerts),
            "created_alerts": created_alerts,
            "total_unread": self.get_unread_count(),
        }

    def get_channel_registry(self) -> Dict[str, Any]:
        """
        Document active notification channels vs extensible adapters.
        Strict academic integrity: never claim SMS or Email is active without working credentials.
        """
        return {
            "channels": [
                {
                    "channel_id": "in_app",
                    "name": "In-App Notification Center & Map Overlay",
                    "status": "active_operational",
                    "description": "Live real-time web interface notifications with unread badge counter and map zooming.",
                },
                {
                    "channel_id": "sms_adapter",
                    "name": "SMS Gateway Adapter (Twilio / CDAC)",
                    "status": "ready_unconfigured",
                    "description": "Extensible provider adapter. Requires TWILIO_AUTH_TOKEN or national CDAC SMS credentials.",
                },
                {
                    "channel_id": "email_adapter",
                    "name": "Email Digest Adapter (SMTP / SES)",
                    "status": "ready_unconfigured",
                    "description": "Extensible provider adapter. Requires SMTP host configuration.",
                },
                {
                    "channel_id": "push_webhook",
                    "name": "Webhook Push Dispatcher",
                    "status": "ready_unconfigured",
                    "description": "Dispatches JSON alert payloads to registered state disaster response webhooks.",
                },
            ],
            "disclaimer": "Only 'in_app' channel is actively delivering notifications. External channels require authenticated gateway credentials.",
        }
