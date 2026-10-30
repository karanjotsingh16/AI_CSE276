"""Unit and integration tests for Accessibility & Field Reporting (Module D & E)."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from accessibility_service import (
    AccessibilityService,
    VALID_INCIDENT_STATUSES,
    VALID_INCIDENT_TYPES,
    VALID_SEGMENT_STATUSES,
    VALID_SEVERITIES,
)


class TestAccessibilityAndReportingService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_accessibility.db"
        self.service = AccessibilityService(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_initialization_and_seeding(self):
        segments = self.service.list_segments()
        self.assertGreaterEqual(len(segments), 5)
        for s in segments:
            self.assertIn("segment_id", s)
            self.assertIn("name", s)
            self.assertIn(s["status"], VALID_SEGMENT_STATUSES)
            self.assertIsInstance(s["coordinates"], list)
            self.assertGreaterEqual(len(s["coordinates"]), 2)

        audit_logs = self.service.list_audit_logs()
        self.assertGreaterEqual(len(audit_logs), 5)
        self.assertEqual(audit_logs[-1]["action"], "seeded")

    def test_list_segments_with_filters(self):
        ri_bhoi_segs = self.service.list_segments(district="Ri-Bhoi")
        self.assertTrue(any("Ri-Bhoi" in s["district"] for s in ri_bhoi_segs))

        open_segs = self.service.list_segments(status="open")
        self.assertTrue(all(s["status"] == "open" for s in open_segs))

        with self.assertRaises(ValueError):
            self.service.list_segments(status="invalid_status")

    def test_submit_incident_report_pending_status(self):
        report = self.service.submit_incident_report(
            title="Landslide near Barapani",
            description="Debris blocking outer northbound lane after heavy shower.",
            incident_type="landslide",
            severity="severe",
            latitude=25.6420,
            longitude=91.9050,
            district="Ri-Bhoi",
            location_name="Barapani Umiam Viewpoint",
            reporter_name="Inspector Sangma",
            reporter_role="field_worker",
        )
        self.assertIn("report_id", report)
        self.assertTrue(report["report_id"].startswith("INC-"))
        self.assertEqual(report["status"], "pending")  # Academic integrity: must start pending
        self.assertEqual(report["incident_type"], "landslide")
        self.assertEqual(report["severity"], "severe")
        self.assertIsNotNone(report["associated_segment_id"])

        # Check audit log entry was created
        logs = self.service.list_audit_logs(entity_type="incident", entity_id=report["report_id"])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "created")
        self.assertEqual(logs[0]["new_status"], "pending")

    def test_submit_incident_validation_errors(self):
        with self.assertRaises(ValueError):
            self.service.submit_incident_report(
                title="Test",
                description="Desc",
                incident_type="earthquake_invalid",
                severity="low",
                latitude=25.0,
                longitude=91.0,
                district="EKH",
                location_name="Test",
                reporter_name="Tester",
            )

        with self.assertRaises(ValueError):
            self.service.submit_incident_report(
                title="Test",
                description="Desc",
                incident_type="flood",
                severity="apocalyptic",
                latitude=25.0,
                longitude=91.0,
                district="EKH",
                location_name="Test",
                reporter_name="Tester",
            )

        with self.assertRaises(ValueError):
            self.service.submit_incident_report(
                title="Test",
                description="Desc",
                incident_type="flood",
                severity="moderate",
                latitude=999.0,
                longitude=91.0,
                district="EKH",
                location_name="Test",
                reporter_name="Tester",
            )

    def test_review_incident_workflow_and_audit(self):
        report = self.service.submit_incident_report(
            title="Bridge fissure",
            description="Structural concrete fissure on bridge pier.",
            incident_type="bridge_damage",
            severity="critical",
            latitude=25.6601,
            longitude=91.8980,
            district="Ri-Bhoi",
            location_name="Umiam Bridge",
            reporter_name="Engineer Roy",
            reporter_role="field_worker",
        )
        report_id = report["report_id"]
        seg_id = report["associated_segment_id"]
        self.assertIsNotNone(seg_id)

        # Review: pending -> verified with cascade to segment
        reviewed = self.service.review_incident(
            report_id=report_id,
            new_status="verified",
            actor="PWD Senior Executive Engineer",
            review_notes="Verified via on-site drone inspection.",
            cascade_to_segment="blocked",
        )
        self.assertEqual(reviewed["status"], "verified")

        # Verify segment status was cascaded to blocked
        seg = self.service.get_segment(seg_id)
        self.assertEqual(seg["status"], "blocked")

        # Check audit trail
        logs = self.service.list_audit_logs(entity_id=report_id)
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0]["action"], "reviewed_verified")
        self.assertEqual(logs[0]["previous_status"], "pending")
        self.assertEqual(logs[0]["new_status"], "verified")

        # Subsequent review: verified -> resolved
        resolved = self.service.review_incident(
            report_id=report_id,
            new_status="resolved",
            actor="PWD Senior Executive Engineer",
            review_notes="Bridge pier reinforcement completed.",
            cascade_to_segment="open",
        )
        self.assertEqual(resolved["status"], "resolved")
        seg_after = self.service.get_segment(seg_id)
        self.assertEqual(seg_after["status"], "open")

    def test_photo_upload_validation(self):
        # Valid photo upload
        safe_url = self.service.save_uploaded_photo("evidence.jpg", b"fake jpeg content bytes")
        self.assertTrue(safe_url.startswith("/api/accessibility/photos/incident_"))
        self.assertTrue(safe_url.endswith(".jpg"))

        # Invalid extension
        with self.assertRaises(ValueError):
            self.service.save_uploaded_photo("malicious.exe", b"binary content")

        # Exceeds max size (> 5MB)
        large_bytes = b"0" * (6 * 1024 * 1024)
        with self.assertRaises(ValueError):
            self.service.save_uploaded_photo("huge.png", large_bytes)

    def test_check_route_against_accessibility(self):
        # Coordinates passing near Umiam (which is restricted in seed data)
        route_coords = [
            (25.6601, 91.8980),
            (25.6420, 91.9050),
            (25.5788, 91.8933),
        ]
        impact = self.service.check_route_against_accessibility(route_coords, buffer_distance_m=1000.0)
        self.assertIn("accessibility_score", impact)
        self.assertIn("impacted_segments", impact)
        self.assertGreaterEqual(impact["impacted_segments_count"], 1)


if __name__ == "__main__":
    unittest.main()
