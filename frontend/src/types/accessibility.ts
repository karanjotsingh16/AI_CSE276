/**
 * Types for Road Accessibility Monitoring (Module D)
 * and Field Incident Reporting (Module E).
 */

export type SegmentStatus = 'open' | 'restricted' | 'blocked' | 'unknown';

export interface RoadSegment {
  segment_id: string;
  name: string;
  road_class: string;
  district: string;
  state: string;
  status: SegmentStatus;
  restriction_details: string | null;
  coordinates: [number, number][];
  last_inspected_at: string;
  updated_at: string;
}

export type IncidentType =
  | 'road_blockage'
  | 'flood'
  | 'landslide'
  | 'bridge_damage'
  | 'road_damage'
  | 'other';

export type IncidentSeverity = 'low' | 'moderate' | 'severe' | 'critical';

export type IncidentStatus = 'pending' | 'verified' | 'rejected' | 'resolved';

export interface IncidentReport {
  report_id: string;
  title: string;
  description: string;
  incident_type: IncidentType;
  severity: IncidentSeverity;
  latitude: number;
  longitude: number;
  district: string;
  location_name: string;
  reporter_name: string;
  reporter_role: string;
  contact_number?: string | null;
  photo_url?: string | null;
  status: IncidentStatus;
  associated_segment_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentReportInput {
  title: string;
  description: string;
  incident_type: IncidentType;
  severity: IncidentSeverity;
  latitude: number;
  longitude: number;
  district: string;
  location_name: string;
  reporter_name: string;
  reporter_role: string;
  contact_number?: string;
  photo_url?: string;
}

export interface IncidentReviewInput {
  new_status: 'verified' | 'rejected' | 'resolved';
  actor: string;
  review_notes: string;
  cascade_to_segment?: 'open' | 'restricted' | 'blocked';
}

export interface AccessibilityAuditLog {
  audit_id: number;
  entity_type: 'incident' | 'road_segment';
  entity_id: string;
  action: string;
  previous_status: string | null;
  new_status: string;
  actor: string;
  review_notes: string;
  timestamp: string;
}

