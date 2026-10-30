/**
 * TypeScript models for Alerts & Notifications System (Module G).
 */

export type NotificationCategory =
  | 'road_closure'
  | 'landslide'
  | 'flood'
  | 'severe_weather'
  | 'vehicle_delay'
  | 'route_disruption'
  | 'route_deviation';

export type NotificationSeverity = 'info' | 'warning' | 'severe' | 'critical';

export interface AppNotification {
  alert_id: string;
  dedup_key: string;
  title: string;
  message: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  source: string;
  latitude: number | null;
  longitude: number | null;
  radius_km: number;
  district: string | null;
  entity_id: string | null;
  is_read: boolean;
  channel: string;
  created_at: string;
}

export interface NotificationChannel {
  channel_id: string;
  name: string;
  status: string;
  description: string;
}

export interface NotificationChannelsResponse {
  channels: NotificationChannel[];
  disclaimer: string;
}

