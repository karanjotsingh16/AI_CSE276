export type AlertSeverity = 'Watch' | 'Alert' | 'Warning' | 'Severe' | 'Advisory' | 'Critical';

export type AlertSourceState = 
  | 'loading' 
  | 'connected' 
  | 'alerts_found' 
  | 'no_alerts' 
  | 'connection_error' 
  | 'spatial_unavailable';

export interface DisasterAlert {
  id: string;
  title: string;
  issuingAgency: string;
  issueTime: string;
  affectedRegion: string;
  severity: AlertSeverity;
  validUntil: string;
  sourceUrl: string;
  category:
    | 'Landslide'
    | 'Heavy Rainfall'
    | 'Flash Flood'
    | 'Road Blockage'
    | 'Fog'
    | 'General'
    | 'Debris Clearance'
    | 'Bridge Load Limit'
    | 'Shoulder Repair'
    | 'Bridge Weight Check'
    | string;
  description: string;
  intersectsRoute: boolean | null; // null if spatial coordinates unavailable
  lat?: number;
  lng?: number;
  radiusKm?: number;
}
