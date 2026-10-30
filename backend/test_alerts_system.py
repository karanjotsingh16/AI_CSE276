"""Unit and integration tests for Alerts and Notifications (Module G)."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from alerts_service import (
    AlertsService,
    VALID_SEVERITIES,
    VALID_CATEGORIES,
)
from accessibility_service import AccessibilityService
from tracking_service import TrackingService
from disruptions_service import DisruptionsService


class TestAlertsSystemService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_alerts.db"
        self.service = AlertsService(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_initialization_and_seeding(self):
        alerts = self.service.list_alerts()
        self.assertGreaterEqual(len(alerts), 3)
        for a in alerts:
            self.assertIn(a["severity"], VALID_SEVERITIES)
            self.assertIn(a["category"], VALID_CATEGORIES)
            self.assertIn("dedup_key", a)
            self.assertFalse(a["is_read"])

    def test_create_and_deduplicate_alert(self):
        # 1. Create first alert
        alt1 = self.service.create_alert(
            title="Flash Flood Warning",
            message="Water overflowing low bridge in Mawkdok valley.",
            category="flood",
            severity="severe",
            source="East Khasi Hills SDMA",
            latitude=25.4200,
            longitude=91.7800,
            entity_id="EVT-FLOOD-001",
        )
        self.assertIsNotNone(alt1)
        self.assertTrue(alt1["alert_id"].startswith("ALT-"))
        self.assertEqual(alt1["category"], "flood")

        # 2. Attempt duplicate creation for same entity on same day
        alt2 = self.service.create_alert(
            title="Flash Flood Warning",
            message="Water overflowing low bridge in Mawkdok valley.",
            category="flood",
            severity="severe",
            source="East Khasi Hills SDMA",
            latitude=25.4200,
            longitude=91.7800,
            entity_id="EVT-FLOOD-001",
        )
        self.assertIsNone(alt2)  # Strictly deduplicated, no spam!

    def test_mark_read_and_unread_count(self):
        initial_unread = self.service.get_unread_count()
        self.assertGreater(initial_unread, 0)

        alerts = self.service.list_alerts(unread_only=True)
        target_id = alerts[0]["alert_id"]

        updated = self.service.mark_alert_read(target_id, is_read=True)
        self.assertTrue(updated["is_read"])

        new_unread = self.service.get_unread_count()
        self.assertEqual(new_unread, initial_unread - 1)

        # Mark all read
        marked_count = self.service.mark_all_read()
        self.assertEqual(marked_count, new_unread)
        self.assertEqual(self.service.get_unread_count(), 0)

    def test_filter_alerts_by_category_and_severity(self):
        warning_alerts = self.service.list_alerts(severity="warning")
        self.assertTrue(all(a["severity"] == "warning" for a in warning_alerts))

        disruption_alerts = self.service.list_alerts(category="route_disruption")
        self.assertTrue(all(a["category"] == "route_disruption" for a in disruption_alerts))

        with self.assertRaises(ValueError):
            self.service.list_alerts(severity="invalid_severity")

    def test_sync_automated_triggers(self):
        # Setup temporary companion services
        acc_db = Path(self.temp_dir) / "test_acc.db"
        acc_svc = AccessibilityService(db_path=acc_db)

        # Update one segment to blocked
        acc_svc.update_segment_status(
            segment_id="SEG-EJH-NH06-02",
            new_status="blocked",
            actor="NHIDCL Executive Engineer",
            restriction_details="Complete road closure due to active mudslide.",
            review_notes="Emergency closure order",
        )

        tr_db = Path(self.temp_dir) / "test_tr.db"
        tr_svc = TrackingService(db_path=tr_db)
        dis_svc = DisruptionsService()

        # Run automated trigger sync
        sync_res = self.service.sync_automated_triggers(
            accessibility_svc=acc_svc,
            disruptions_svc=dis_svc,
            tracking_svc=tr_svc,
        )
        self.assertIn("created_count", sync_res)
        self.assertGreaterEqual(sync_res["created_count"], 1)

        # Re-running sync immediately should create 0 new alerts (all deduplicated!)
        sync_res2 = self.service.sync_automated_triggers(
            accessibility_svc=acc_svc,
            disruptions_svc=dis_svc,
            tracking_svc=tr_svc,
        )
        self.assertEqual(sync_res2["created_count"], 0)

    def test_channel_registry_academic_integrity(self):
        registry = self.service.get_channel_registry()
        self.assertIn("channels", registry)
        channels = {c["channel_id"]: c["status"] for c in registry["channels"]}
        self.assertEqual(channels["in_app"], "active_operational")
        self.assertEqual(channels["sms_adapter"], "ready_unconfigured")
        self.assertEqual(channels["email_adapter"], "ready_unconfigured")
        self.assertIn("disclaimer", registry)


if __name__ == "__main__":
    unittest.main()

