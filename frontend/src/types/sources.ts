export type SourceStatus = 
  | 'Live Connected' 
  | 'Configured' 
  | 'Reference Only' 
  | 'Planned Proxy';

export interface TrustedDataSource {
  id: string;
  name: string;
  provider: string;
  category: 'Government Alerts' | 'Weather Forecast' | 'Precipitation Radar' | 'Elevation & DEM' | 'Landslide Hazard' | 'Forest Fire Hazard' | 'Tsunami / Coastal';
  purpose: string;
  url: string;
  status: SourceStatus;
  lastChecked: string;
  notes: string;
}
