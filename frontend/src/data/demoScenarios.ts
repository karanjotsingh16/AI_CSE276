import { RouteAlternative } from '../types/route';

// Realistic road waypoints following actual Meghalaya highways
// NH-206 Corridor: Shillong -> Mylliem -> Laitlyngkot -> Mawkdok Dympep Bridge -> Sohra
export const SHILLONG_TO_SOHRA_ROUTE_A: [number, number][] = [
  [25.5788, 91.8933], // Shillong Police Bazar
  [25.5645, 91.8792], // Laban / Cantonment
  [25.5480, 91.8610], // Upper Shillong Peak gate
  [25.5312, 91.8488], // 5th Mile
  [25.5120, 91.8415], // 7th Mile / Elephant Falls Junction
  [25.4890, 91.8320], // Mylliem Village
  [25.4650, 91.8280], // Mylliem Kyndong
  [25.4380, 91.8210], // Wahlyngkhat
  [25.4120, 91.8150], // Laitlyngkot Viewpoint
  [25.3850, 91.8020], // Mawkdok Dympep Valley View Bridge
  [25.3620, 91.7910], // Wakaba Falls bend
  [25.3340, 91.7720], // Mawmluh ridge road
  [25.3050, 91.7510], // Sohra entrance gate / Khasi monoliths
  [25.2890, 91.7410], // Saitsohpen
  [25.2750, 91.7323]  // Sohra Cherrapunji Center
];

// Western Highland Bypass: Shillong -> Mawngap -> Mawphlang Sacred Forest -> Tyrsad -> Sohra
export const SHILLONG_TO_SOHRA_ROUTE_B: [number, number][] = [
  [25.5788, 91.8933], // Shillong
  [25.5520, 91.8540], // Upper Shillong
  [25.5290, 91.8120], // Mawngap Junction
  [25.5010, 91.7650], // Mawphlang Sacred Forest
  [25.4610, 91.7420], // Ladmawphlang
  [25.4120, 91.7280], // Tyrsad Highland pass
  [25.3680, 91.7150], // West Canyon Rim
  [25.3210, 91.7180], // Mawmluh cave approach
  [25.2950, 91.7250], // Sohra rim
  [25.2750, 91.7323]  // Sohra Cherrapunji Center
];

// Eastern Valley Ridge: Shillong -> Smit -> Laitlum Canyons -> Pynursla road -> Sohra
export const SHILLONG_TO_SOHRA_ROUTE_C: [number, number][] = [
  [25.5788, 91.8933], // Shillong
  [25.5590, 91.9210], // Nongthymmai
  [25.5340, 91.9560], // Smit Village
  [25.4980, 91.9420], // Laitlum Ridge Road
  [25.4410, 91.9120], // Nongjri descent
  [25.3950, 91.8850], // Wahkhen valley crossing
  [25.3420, 91.8320], // East canyon link
  [25.3010, 91.7850], // Sohra East approach
  [25.2750, 91.7323]  // Sohra Cherrapunji Center
];

// Fallback route alternatives for Shillong -> Sohra
export const DEFAULT_SHILLONG_SOHRA_ROUTES: RouteAlternative[] = [
  {
    id: 'route-a',
    name: 'Route A — NH 206 Direct Corridor',
    via: 'Via Mylliem & Mawkdok Gorge Bridge',
    status: 'RECOMMENDED',
    distanceKm: 53.8,
    durationMinutes: 84, // 1h 24m
    disasterRiskScore: 24, // low-moderate
    weatherRiskScore: 32,
    terrainExposureScore: 28,
    accessibilityScore: 88,
    logisticsScore: 82,
    warnings: [
      'Frequent low-lying cloud fog at Mawkdok Bridge',
      'Dual lane paved surface; moderate grade at 7th Mile'
    ],
    tradeoffs: 'Fastest transit time and widest paved road. Best fuel efficiency and highest cellular telemetry coverage.',
    coordinates: SHILLONG_TO_SOHRA_ROUTE_A,
    color: '#2563eb', // Blue primary
    source: 'NER High-Resolution Road Network (NH-206)',
    isSimulated: false,
    elevationProfile: {
      minMeters: 1180,
      maxMeters: 1720,
      ascentMeters: 380
    }
  },
  {
    id: 'route-b',
    name: 'Route B — SH-5 Highland Bypass',
    via: 'Via Mawphlang Sacred Forest & Ladmawphlang',
    status: 'ALTERNATIVE',
    distanceKm: 64.2,
    durationMinutes: 112, // 1h 52m
    disasterRiskScore: 38,
    weatherRiskScore: 45,
    terrainExposureScore: 52,
    accessibilityScore: 72,
    logisticsScore: 68,
    warnings: [
      'Steep 12% grade ascent near Tyrsad pass',
      'Exposed ridge winds during monsoon fronts'
    ],
    tradeoffs: 'Avoids main valley congestion, but increases transit time by 28 mins and has higher fuel consumption.',
    coordinates: SHILLONG_TO_SOHRA_ROUTE_B,
    color: '#d97706', // Amber alternative
    source: 'NER State Highway Network (SH-5)',
    isSimulated: false,
    elevationProfile: {
      minMeters: 1220,
      maxMeters: 1845,
      ascentMeters: 625
    }
  },
  {
    id: 'route-c',
    name: 'Route C — Eastern Canyon Escarpment',
    via: 'Via Smit & Laitlum Gorge Bypass',
    status: 'NOT RECOMMENDED',
    distanceKm: 71.5,
    durationMinutes: 146, // 2h 26m
    disasterRiskScore: 68,
    weatherRiskScore: 58,
    terrainExposureScore: 74,
    accessibilityScore: 45,
    logisticsScore: 46,
    warnings: [
      'Active minor rockfall debris reported near East Escarpment',
      'Narrow single-lane mountain road with sharp blind hairpins'
    ],
    tradeoffs: 'Significantly longer journey time, high landslide susceptibility index, and limited mobile network coverage.',
    coordinates: SHILLONG_TO_SOHRA_ROUTE_C,
    color: '#dc2626', // Red warning
    source: 'NER Rural Mountain Arterial Network',
    isSimulated: false,
    elevationProfile: {
      minMeters: 940,
      maxMeters: 1780,
      ascentMeters: 840
    }
  }
];
