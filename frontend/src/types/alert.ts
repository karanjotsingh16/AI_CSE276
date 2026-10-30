export type AlertSeverity = 'Watch' | 'Alert' | 'Warning' | 'Severe';

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
  category: 'Landslide' | 'Heavy Rainfall' | 'Flash Flood' | 'Road Blockage' | 'Fog' | 'General';
  description: string;
  intersectsRoute: boolean | null; // null if spatial coordinates unavailable
  lat?: number;
  lng?: number;
  radiusKm?: number;
}
