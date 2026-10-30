import { TrustedDataSource } from '../types/sources';

export const TRUSTED_DATA_SOURCES: TrustedDataSource[] = [
  {
    id: 'sachet-alerts',
    name: 'NDMA / SACHET CAP Integrated Alert System',
    provider: 'National Disaster Management Authority (NDMA)',
    category: 'Government Alerts',
    purpose: 'Standardized Common Alerting Protocol (CAP) disaster warnings, heavy rainfall watches, and regional landslide alerts.',
    url: 'https://sachet.ndma.gov.in/',
    status: 'Configured',
    lastChecked: 'Live check on load (browser CORS fallback to verified regional CAP notices)',
    notes: 'Official government alert portal. Direct client-side browser fetch requires FastAPI proxy; verified fallback feed active.'
  },
  {
    id: 'open-meteo-weather',
    name: 'Open-Meteo Weather API',
    provider: 'Open-Meteo / WMO 0.25° Seamless Numerical Model',
    category: 'Weather Forecast',
    purpose: 'Hourly precipitation probability, rainfall rate (mm), wind speed (km/h), and temperature along route waypoints.',
    url: 'https://open-meteo.com/en/docs',
    status: 'Live Connected',
    lastChecked: 'Active real-time query on mission origin/destination',
    notes: 'Direct client-side JSON API with zero authentication key requirement.'
  },
  {
    id: 'rainviewer-radar',
    name: 'RainViewer Live Precipitation Radar API',
    provider: 'RainViewer Meteorological Radar Composite',
    category: 'Precipitation Radar',
    purpose: 'Past 2-hour radar reflectivity tile maps showing actual convective precipitation cells over the Meghalaya plateau.',
    url: 'https://www.rainviewer.com/api/weather-maps-api.html',
    status: 'Live Connected',
    lastChecked: 'Active frame metadata sync (api.rainviewer.com/public/weather-maps.json)',
    notes: 'Observed composite radar frames with multi-frame animation cycling.'
  },
  {
    id: 'open-meteo-elevation',
    name: 'Open-Meteo Elevation API (Copernicus DEM)',
    provider: 'Copernicus 90m / 30m Global Digital Elevation Model',
    category: 'Elevation & DEM',
    purpose: 'Sampling terrain elevation profiles, gradient slopes, and mountain pass ascents along route corridors.',
    url: 'https://open-meteo.com/en/docs/elevation-api',
    status: 'Live Connected',
    lastChecked: 'Active real-time altitude queries',
    notes: 'Free public DEM service providing precise topographical context for route risk calculation.'
  },
  {
    id: 'gsi-landslides',
    name: 'Geological Survey of India (GSI) Landslide Susceptibility',
    provider: 'GSI National Landslide Susceptibility Mapping (NLSM)',
    category: 'Landslide Hazard',
    purpose: 'Hazard zonation reference and historical slope instability classification for NH-6 and NH-206 ghat sections.',
    url: 'https://www.gsi.gov.in/webcenter/portal/OCBIS/pageGeoLandslide',
    status: 'Reference Only',
    lastChecked: 'GSI Meghalaya Pilot Zone Assessment',
    notes: 'Official reference layer for terrain slope threshold calibration in the route scoring model.'
  },
  {
    id: 'fsi-forest-fires',
    name: 'Forest Survey of India (FSI) Fire Warning System',
    provider: 'Forest Survey of India / SNPP-VIIRS & MODIS Sensors',
    category: 'Forest Fire Hazard',
    purpose: 'Forest fire alert monitoring and dry season biomass burning risk assessment across reserve forest tracts.',
    url: 'https://vanagrah.fsi.gov.in/',
    status: 'Reference Only',
    lastChecked: 'FSI VanAgrah National Portal',
    notes: 'Calibrated seasonal hazard reference for rural jungle transit roads.'
  },
  {
    id: 'incois-tsunami',
    name: 'INCOIS Indian Tsunami Early Warning Centre (ITEWC)',
    provider: 'Indian National Centre for Ocean Information Services',
    category: 'Tsunami / Coastal',
    purpose: 'National coastal seismic and oceanic inundation monitoring registry.',
    url: 'https://incois.gov.in/portal/datainfo/tsunami.jsp',
    status: 'Reference Only',
    lastChecked: 'INCOIS ITEWC Portal',
    notes: 'Verified reference authority; inland mountainous NER routes are flagged zero-inundation for this hazard.'
  }
];
