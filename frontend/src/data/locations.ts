import { LocationPoint } from '../types/mission';

export const NER_LOCATIONS: LocationPoint[] = [
  {
    id: 'shillong',
    name: 'Shillong (HQ Logistics Hub)',
    state: 'Meghalaya',
    lat: 25.5788,
    lng: 91.8933,
    elevationMeters: 1496,
    type: 'hub',
    description: 'Central NER disaster logistics coordination center & civil hospital staging depot'
  },
  {
    id: 'sohra',
    name: 'Sohra / Cherrapunji (Southern Hills)',
    state: 'Meghalaya',
    lat: 25.2750,
    lng: 91.7323,
    elevationMeters: 1430,
    type: 'destination',
    description: 'High precipitation monsoon corridor with steep canyon access routes'
  },
  {
    id: 'mairang',
    name: 'Mairang (West Khasi Hills Transit)',
    state: 'Meghalaya',
    lat: 25.5653,
    lng: 91.6375,
    elevationMeters: 1620,
    type: 'outpost',
    description: 'Highland plateau transit point with vulnerable ridge cuts'
  },
  {
    id: 'dawki',
    name: 'Dawki (Border River Outpost)',
    state: 'Meghalaya',
    lat: 25.1911,
    lng: 92.0232,
    elevationMeters: 85,
    type: 'outpost',
    description: 'Umngot river crossing border outpost and low-altitude supply terminal'
  },
  {
    id: 'pynursla',
    name: 'Pynursla (Southern Ridge Outpost)',
    state: 'Meghalaya',
    lat: 25.3112,
    lng: 91.8942,
    elevationMeters: 1390,
    type: 'outpost',
    description: 'Southern ridge town on NH-206 en route to Dawki border terminal'
  },
  {
    id: 'mawphlang',
    name: 'Mawphlang (Central Highland Junction)',
    state: 'Meghalaya',
    lat: 25.4518,
    lng: 91.7568,
    elevationMeters: 1780,
    type: 'outpost',
    description: 'Mid-plateau highland transit town along the western ridge corridor'
  },
  {
    id: 'smit_meghalaya',
    name: 'Smit (Eastern Plateau Supply Point)',
    state: 'Meghalaya',
    lat: 25.5186,
    lng: 91.9462,
    elevationMeters: 1610,
    type: 'outpost',
    description: 'Rural plateau agricultural and relief distribution town'
  },
  {
    id: 'upper_shillong',
    name: 'Upper Shillong (7th Mile Staging Hub)',
    state: 'Meghalaya',
    lat: 25.5415,
    lng: 91.8490,
    elevationMeters: 1820,
    type: 'hub',
    description: 'High-altitude western junction splitting corridors toward Sohra and Mairang'
  },
  {
    id: 'police_bazar_shillong',
    name: 'Police Bazar, Shillong',
    state: 'Meghalaya',
    lat: 25.5769,
    lng: 91.8831,
    elevationMeters: 1490,
    type: 'hub',
    description: 'Commercial core and central urban transit node of Shillong'
  },
  {
    id: 'laitumkhrah_shillong',
    name: 'Laitumkhrah, Shillong',
    state: 'Meghalaya',
    lat: 25.5712,
    lng: 91.8995,
    elevationMeters: 1515,
    type: 'hub',
    description: 'Eastern Shillong hospital, institutional, and municipal distribution zone'
  }
];

export const DEFAULT_ORIGIN_ID = 'shillong';
export const DEFAULT_DESTINATION_ID = 'sohra';

// Pilot area bounding box (Meghalaya - Central NER)
export const NER_PILOT_BOUNDS: [[number, number], [number, number]] = [
  [25.05, 91.45], // South-West
  [26.25, 92.35]  // North-East
];

export const NER_CENTER: [number, number] = [25.45, 91.82];
export const NER_DEFAULT_ZOOM = 10;
