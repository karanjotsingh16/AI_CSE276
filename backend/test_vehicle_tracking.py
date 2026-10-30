"""Unit and integration tests for GPS Vehicle & Delivery Tracking (Module F)."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tracking_service import (
    TrackingService,
    VALID_VEHICLE_TYPES,
    VALID_DELIVERY_STATUSES,
    VALID_GOODS_CATEGORIES,
    ROUTE_DEVIATION_THRESHOLD_M,
)


class TestVehicleTrackingService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_tracking.db"
        self.service = TrackingService(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_initialization_and_seeding(self):
        vehicles = self.service.list_vehicles()
        self.assertGreaterEqual(len(vehicles), 4)
        for v in vehicles:
            self.assertIn(v["vehicle_type"], VALID_VEHICLE_TYPES)
            self.assertGreater(v["capacity_kg"], 0.0)

        deliveries = self.service.list_deliveries()
        self.assertGreaterEqual(len(deliveries), 2)
        for d in deliveries:
            self.assertIn(d["status"], VALID_DELIVERY_STATUSES)
            self.assertIn(d["goods_category"], VALID_GOODS_CATEGORIES)
            self.assertIsInstance(d["planned_route_geometry"], list)

    def test_register_vehicle(self):
        veh = self.service.register_vehicle(
            vehicle_id="TR-01-ME-9999",
            name="Emergency 4x4 Quick Response",
            vehicle_type="4x4",
            capacity_kg=1500.0,
            assigned_driver_name="Officer Nongbri",
            assigned_driver_contact="+91 99999 11111",
            initial_lat=25.5788,
            initial_lng=91.8933,
        )
        self.assertEqual(veh["vehicle_id"], "TR-01-ME-9999")
        self.assertEqual(veh["vehicle_type"], "4x4")
        self.assertEqual(veh["current_latitude"], 25.5788)

        # Duplicate vehicle check
        with self.assertRaises(ValueError):
            self.service.register_vehicle(
                vehicle_id="TR-01-ME-9999",
                name="Duplicate",
                vehicle_type="4x4",
                capacity_kg=1000.0,
                assigned_driver_name="Test",
            )

    def test_create_delivery_and_eta(self):
        geometry = [
            [25.5788, 91.8933],
            [25.5600, 91.7500],
            [25.5650, 91.6400],
        ]
        delivery = self.service.create_delivery(
            vehicle_id="ML-05-TR-1042",
            title="Cold-Chain Vaccine Shipment to Mairang",
            goods_category="Vaccines / Cold Chain",
            priority="Emergency",
            origin_name="Pasteur Institute Shillong",
            origin_lat=25.5788,
            origin_lng=91.8933,
            destination_name="Mairang CHC",
            destination_lat=25.5650,
            destination_lng=91.6400,
            planned_distance_km=42.5,
            planned_duration_minutes=55.0,
            planned_route_geometry=geometry,
        )
        self.assertTrue(delivery["delivery_id"].startswith("DEL-"))
        self.assertEqual(delivery["status"], "in_transit")
        self.assertIsNotNone(delivery["estimated_arrival_time"])
        self.assertFalse(delivery["is_deviated"])

    def test_telemetry_on_route_and_progress(self):
        deliveries = self.service.list_deliveries(status="in_transit")
        self.assertGreater(len(deliveries), 0)
        deliv = deliveries[0]

        # Submit telemetry exactly along second waypoint
        coords = deliv["planned_route_geometry"]
        wp = coords[1]
        telemetry_res = self.service.record_telemetry(
            vehicle_id=deliv["vehicle_id"],
            latitude=wp[0],
            longitude=wp[1],
            speed_kph=34.0,
            bearing=180.0,
            delivery_id=deliv["delivery_id"],
            source="real_gps",
        )
        self.assertFalse(telemetry_res["is_deviated"])
        self.assertLess(telemetry_res["deviation_distance_m"], 50.0)
        self.assertEqual(telemetry_res["telemetry"]["telemetry_source"], "real_gps")

    def test_route_deviation_detection(self):
        deliveries = self.service.list_deliveries(status="in_transit")
        deliv = deliveries[0]

        # Telemetry displaced 2 km from route
        off_lat = deliv["origin_lat"] + 0.02
        off_lng = deliv["origin_lng"] + 0.02

        telemetry_res = self.service.record_telemetry(
            vehicle_id=deliv["vehicle_id"],
            latitude=off_lat,
            longitude=off_lng,
            speed_kph=20.0,
            bearing=45.0,
            delivery_id=deliv["delivery_id"],
            source="real_gps",
        )
        self.assertTrue(telemetry_res["is_deviated"])
        self.assertGreater(telemetry_res["deviation_distance_m"], ROUTE_DEVIATION_THRESHOLD_M)

    def test_step_simulated_telemetry_and_disclaimer(self):
        deliveries = self.service.list_deliveries(status="in_transit")
        deliv = deliveries[0]

        sim_res = self.service.step_simulated_telemetry(
            delivery_id=deliv["delivery_id"], progress_step_pct=10.0, simulate_deviation=False
        )
        self.assertEqual(sim_res["telemetry"]["telemetry_source"], "simulated_demo")
        self.assertIn("DEMONSTRATION MODE", sim_res["disclaimer"])

        # History log check
        history = self.service.get_telemetry_history(deliv["vehicle_id"])
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["telemetry_source"], "simulated_demo")

    def test_delivery_status_transitions(self):
        deliveries = self.service.list_deliveries()
        deliv_id = deliveries[0]["delivery_id"]

        updated = self.service.update_delivery_status(deliv_id, "delayed", delay_reason="NH-6 rockfall hold")
        self.assertEqual(updated["status"], "delayed")
        self.assertEqual(updated["delay_reason"], "NH-6 rockfall hold")

        delivered = self.service.update_delivery_status(deliv_id, "delivered")
        self.assertEqual(delivered["status"], "delivered")
        self.assertIsNotNone(delivered["actual_arrival_time"])


if __name__ == "__main__":
    unittest.main()

