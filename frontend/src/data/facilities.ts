import { CriticalFacility } from '../types/infrastructure';

export const CRITICAL_FACILITIES: CriticalFacility[] = [
  // Hospitals & Clinics
  {
    id: 'hosp-1',
    name: 'NEIGRIHMS Tertiary Care Hospital',
    category: 'hospital',
    lat: 25.5925,
    lng: 91.9388,
    address: 'Mawdiangdiang, Shillong, Meghalaya 793018',
    capacityOrType: '550 Beds / Trauma Level 1 ICU',
    operationalStatus: 'Operational',
    source: 'OpenStreetMap (amenity=hospital) & Meghalaya Health Directory',
    disclaimer: 'Point represents mapped facility location; verify active capacity with dispatch'
  },
  {
    id: 'hosp-2',
    name: 'Shillong Civil Hospital',
    category: 'hospital',
    lat: 25.5714,
    lng: 91.8805,
    address: 'Labān, Shillong, Meghalaya 793004',
    capacityOrType: '280 Beds / Emergency Surgical Unit',
    operationalStatus: 'Operational',
    source: 'OpenStreetMap (amenity=hospital)',
    disclaimer: 'Public district general hospital emergency staging base'
  },
  {
    id: 'hosp-3',
    name: 'Sohra Community Health Centre (CHC)',
    category: 'hospital',
    lat: 25.2810,
    lng: 91.7315,
    address: 'Sohra Bazar, Cherrapunji, Meghalaya 793108',
    capacityOrType: '40 Beds / Urgent Primary Care',
    operationalStatus: 'Operational',
    source: 'OpenStreetMap (amenity=hospital)',
    disclaimer: 'Frontline mountain health clinic for southern East Khasi Hills'
  },
  {
    id: 'hosp-4',
    name: 'Jowai Civil Hospital',
    category: 'hospital',
    lat: 25.4520,
    lng: 92.2085,
    address: 'Panaliar, Jowai, Meghalaya 793150',
    capacityOrType: '150 Beds / Regional Emergency Ward',
    operationalStatus: 'Operational',
    source: 'OpenStreetMap (amenity=hospital)',
    disclaimer: 'Eastern Jaintia sub-regional referral facility'
  },

  // Relief Centres & Shelters
  {
    id: 'relief-1',
    name: 'Meghalaya State Disaster Management Authority (SDMA) Emergency Ops Center',
    category: 'relief',
    lat: 25.5802,
    lng: 91.8970,
    address: 'Secretariat Hills, Lower Lachumiere, Shillong 793001',
    capacityOrType: 'State Central Command & Relief Distribution Staging',
    operationalStatus: 'Standby',
    source: 'SDMA Meghalaya Public Infrastructure Directory',
    disclaimer: 'Primary governmental coordination bunker for cloudburst and landslide operations'
  },
  {
    id: 'relief-2',
    name: 'Sohra Multipurpose Cyclone & Monsoon Shelter',
    category: 'relief',
    lat: 25.2690,
    lng: 91.7280,
    address: 'Saitsohpen, Sohra, Meghalaya 793108',
    capacityOrType: 'Capacity 600 Evacuees / Solar Microgrid & Water Filtration',
    operationalStatus: 'Operational',
    source: 'State Disaster Response Logistics Register',
    disclaimer: 'Reinforced concrete emergency refuge station with helicopter drop pad'
  },
  {
    id: 'relief-3',
    name: 'Upper Shillong Peak Emergency Shelter Post',
    category: 'relief',
    lat: 25.5412,
    lng: 91.8490,
    address: 'Air Force Station Road, Shillong 793005',
    capacityOrType: 'Highland Shelter / 350 Persons',
    operationalStatus: 'Operational',
    source: 'Civil Defence & Home Guards Directory',
    disclaimer: 'Emergency cold-weather shelter on the highland divide'
  },

  // Logistics Hubs & Warehouses
  {
    id: 'logistics-1',
    name: 'Food Corporation of India (FCI) Regional Depot Mawlai',
    category: 'logistics',
    lat: 25.6025,
    lng: 91.8840,
    address: 'Mawlai Mawiong, Shillong, Meghalaya 793017',
    capacityOrType: '12,000 MT Grain & Relief Storage',
    operationalStatus: 'Active Depot',
    source: 'FCI Public Warehouse Database & OpenStreetMap',
    disclaimer: 'Strategic central food ration stockpile for East Khasi Hills'
  },
  {
    id: 'logistics-2',
    name: 'Meghalaya State Transport Central Fleet Depot',
    category: 'logistics',
    lat: 25.5760,
    lng: 91.8750,
    address: 'Police Bazar Hub, Shillong 793001',
    capacityOrType: '4×4 High-Clearance Fleet & Fuel Reserve 45,000L',
    operationalStatus: 'Active Depot',
    source: 'MTC Department Records',
    disclaimer: 'Vehicle staging base for mountain terrain convoys'
  },
  {
    id: 'logistics-3',
    name: 'Guwahati Multi-Modal Inland Logistics Freight Terminal',
    category: 'logistics',
    lat: 26.1380,
    lng: 91.7450,
    address: 'Beltola Industrial Corridor, Guwahati 781028',
    capacityOrType: 'Heavy Truck Railhead & National Relief Transfer Depot',
    operationalStatus: 'Active Depot',
    source: 'National Logistics Portal & OSM',
    disclaimer: 'Primary gateway supplying bulk freight from mainland India into NER'
  }
];
