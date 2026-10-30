/**
 * TypeScript models for GPS Vehicle & Delivery Tracking (Module F).
 */

export type VehicleType = '4x4' | 'Van' | 'Heavy Truck' | 'Electric Van' | 'Pickup';

export type DeliveryStatus =
  | 'scheduled'
  | 'dispatched'
  | 'in_transit'
  | 'delayed'
  | 'delivered'
  | 'interrupted';

export type GoodsCategory =
  | 'Medical Supplies'
  | 'Food Supplies'
  | 'Relief Materials'
  | 'General Cargo'
  | 'Vaccines / Cold Chain';

export type DeliveryPriority = 'Emergency' | 'High' | 'Normal' | 'Low';

export type TelemetryMode = 'real_gps' | 'simulated_demo';

export interface Vehicle {
  vehicle_id: string;
  name: string;
  vehicle_type: VehicleType;
  capacity_kg: number;
  assigned_driver_name: string;
  assigned_driver_contact: string | null;
  current_latitude: number | null;
  current_longitude: number | null;
  current_speed_kph: number;
  current_bearing: number;
  last_telemetry_at: string | null;
  telemetry_mode: TelemetryMode;
  created_at: string;
  updated_at: string;
}

export interface Delivery {
  delivery_id: string;
  vehicle_id: string;
  title: string;
  goods_category: GoodsCategory;
  priority: DeliveryPriority;
  origin_name: string;
  origin_lat: number;
  origin_lng: number;
  destination_name: string;
  destination_lat: number;
  destination_lng: number;
  dispatch_time: string | null;
  estimated_arrival_time: string | null;
  actual_arrival_time: string | null;
  status: DeliveryStatus;
  planned_distance_km: number;
  planned_duration_minutes: number;
  planned_route_geometry: [number, number][];
  progress_pct: number;
  is_deviated: boolean;
  deviation_distance_m: number;
  delay_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeliveryCreateInput {
  vehicle_id: string;
  title: string;
  goods_category: GoodsCategory;
  priority: DeliveryPriority;
  origin_name: string;
  origin_lat: number;
  origin_lng: number;
  destination_name: string;
  destination_lat: number;
  destination_lng: number;
  planned_distance_km: number;
  planned_duration_minutes: number;
  planned_route_geometry: [number, number][];
  dispatch_immediately?: boolean;
}

export interface TelemetryResponse {
  vehicle: Vehicle;
  telemetry: {
    latitude: number;
    longitude: number;
    speed_kph: number;
    bearing: number;
    telemetry_source: TelemetryMode;
    timestamp: string;
  };
  delivery_id: string | null;
  is_deviated: boolean;
  deviation_distance_m: number;
  progress_pct: number;
  disclaimer: string;
}

