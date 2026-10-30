import { NER_LOCATIONS } from '../data/locations';
import { LocationPoint } from '../types/mission';
import {
  GeocodedLocationResult,
  GeocodeSearchResponse,
  RegionsCatalogResponse,
} from '../types/geocoding';
import { getApiBaseUrl } from './routeService';

const IN_COVERAGE_IDS = new Set([
  'shillong',
  'police_bazar_shillong',
  'laitumkhrah_shillong',
  'upper_shillong',
  'smit_meghalaya',
  'mawphlang',
  'sohra',
  'mairang',
  'pynursla',
  'dawki',
]);

function buildOfflineFallbackResult(loc: LocationPoint): GeocodedLocationResult {
  const inGraph = IN_COVERAGE_IDS.has(loc.id);
  const expandIds = new Set(['jowai', 'nongpoh', 'guwahati']);
  const isExpandable = expandIds.has(loc.id);

  return {
    place_id: loc.id,
    name: loc.name,
    display_name: `${loc.name}, ${loc.state}, India`,
    state: loc.state,
    lat: loc.lat,
    lng: loc.lng,
    elevation_m: loc.elevationMeters,
    place_type: loc.type,
    source: 'offline_client_fallback',
    description: loc.description,
    coverage: {
      within_loaded_graph: inGraph,
      status: inGraph
        ? 'routable_in_loaded_graph'
        : isExpandable
          ? 'supported_region_not_downloaded'
          : 'outside_all_catalog_regions',
      region_id: inGraph
        ? 'meghalaya_shillong_sohra'
        : loc.id === 'jowai'
          ? 'meghalaya_jaintia_jowai'
          : 'assam_guwahati_nongpoh',
      region_name: inGraph
        ? 'East & West Khasi Hills (Shillong–Sohra)'
        : loc.id === 'jowai'
          ? 'Jaintia Hills NH-6 Corridor'
          : 'Brahmaputra Valley–Ri-Bhoi Corridor',
      nearest_node_id: null,
      nearest_node_lat: null,
      nearest_node_lng: null,
      snap_distance_m: inGraph ? 25.0 : 15000.0,
      max_snap_distance_m: 3000.0,
      matching_catalog_regions: inGraph ? ['meghalaya_shillong_sohra'] : [],
      acquire_command: isExpandable
        ? `python backend/region_manager.py --acquire ${
            loc.id === 'jowai' ? 'meghalaya_jaintia_jowai' : 'assam_guwahati_nongpoh'
          }`
        : null,
      message: inGraph
        ? 'Within Shillong–Sohra road network coverage.'
        : 'Outside currently loaded Shillong–Sohra road graph (> 3,000 m snap limit).',
    },
  };
}

export function convertGeocodedToLocationPoint(
  item: GeocodedLocationResult
): LocationPoint {
  const validType =
    item.place_type === 'hub' ||
    item.place_type === 'depot' ||
    item.place_type === 'outpost' ||
    item.place_type === 'destination'
      ? item.place_type
      : 'destination';

  return {
    id: item.place_id,
    name: item.name,
    state: item.state || 'India',
    lat: item.lat,
    lng: item.lng,
    elevationMeters: item.elevation_m ?? 1000,
    type: validType,
    description:
      item.description ||
      item.display_name ||
      `${item.lat.toFixed(4)}°N, ${item.lng.toFixed(4)}°E`,
  };
}

export async function searchLocations(
  query: string,
  limit: number = 6
): Promise<GeocodeSearchResponse> {
  const trimmed = query.trim();
  if (!trimmed) {
    throw new Error('Please enter a city, town, hub name, or "lat, lng" coordinates.');
  }

  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/geocode?q=${encodeURIComponent(trimmed)}&limit=${limit}`;

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    if (!res.ok) {
      let detail = `Location lookup failed (HTTP ${res.status}).`;
      try {
        const errJson = await res.json();
        if (typeof errJson?.detail === 'string') {
          detail = errJson.detail;
        }
      } catch {
        // Ignore JSON parse error
      }
      throw new Error(detail);
    }

    return (await res.json()) as GeocodeSearchResponse;
  } catch (err: unknown) {
    if (err instanceof Error && err.message.includes('Latitude')) {
      throw err;
    }
    // Client-side offline fallback against NER_LOCATIONS if backend is unreachable
    const qLow = trimmed.toLowerCase();
    const matches = NER_LOCATIONS.filter(
      (l) =>
        l.name.toLowerCase().includes(qLow) ||
        l.state.toLowerCase().includes(qLow) ||
        l.id.toLowerCase().includes(qLow)
    ).map(buildOfflineFallbackResult);

    return {
      query: trimmed,
      geocoder_source: 'offline_client_fallback',
      attribution: 'Place data © OpenStreetMap contributors (ODbL)',
      count: matches.length,
      results: matches,
    };
  }
}

export async function fetchDefaultLocationSuggestions(): Promise<GeocodedLocationResult[]> {
  const baseUrl = getApiBaseUrl();
  try {
    const res = await fetch(`${baseUrl}/api/geocode/suggestions`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data?.suggestions) && data.suggestions.length > 0) {
        return data.suggestions as GeocodedLocationResult[];
      }
    }
  } catch {
    // Fallback below
  }
  return NER_LOCATIONS.map(buildOfflineFallbackResult);
}

export async function fetchRegionsCatalog(): Promise<RegionsCatalogResponse | null> {
  const baseUrl = getApiBaseUrl();
  try {
    const res = await fetch(`${baseUrl}/api/regions`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      return (await res.json()) as RegionsCatalogResponse;
    }
  } catch {
    // Ignore when backend is offline
  }
  return null;
}

