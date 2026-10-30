import { LocationPoint, PriorityType } from '../types/mission';
import {
  BackendRouteCalculationResponse,
  BackendSingleRoute,
  RouteAlternative,
  RouteErrorCode,
  RoutePreference,
} from '../types/route';
import { evaluateAndRankRoutes } from '../logic/routeScoring';
import { formatDurationHoursMinutes } from '../logic/formatters';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (typeof configured === 'string' && configured.trim().length > 0) {
    return configured.trim().replace(/\/+$/, '');
  }
  return DEFAULT_API_BASE_URL;
}

export class RouteApiError extends Error {
  public readonly code: RouteErrorCode;
  public readonly title: string;
  public readonly detail: string;
  public readonly status: number | null;

  constructor(
    code: RouteErrorCode,
    title: string,
    detail: string,
    status: number | null = null
  ) {
    super(detail);
    this.name = 'RouteApiError';
    this.code = code;
    this.title = title;
    this.detail = detail;
    this.status = status;
  }
}

/**
 * Converts GeoJSON LineString coordinates ([longitude, latitude])
 * returned by the backend into Leaflet polyline coordinates ([latitude, longitude]).
 */
function convertGeoJSONToLeafletCoords(
  geoJsonCoords: [number, number][]
): [number, number][] {
  if (!Array.isArray(geoJsonCoords)) {
    return [];
  }
  return geoJsonCoords
    .filter(
      (pt): pt is [number, number] =>
        Array.isArray(pt) &&
        pt.length >= 2 &&
        typeof pt[0] === 'number' &&
        typeof pt[1] === 'number' &&
        Number.isFinite(pt[0]) &&
        Number.isFinite(pt[1])
    )
    .map(([lng, lat]) => [lat, lng]);
}

function buildRouteAlternative(
  backendRoute: BackendSingleRoute,
  variant: 'estimated_fastest' | 'shortest' | 'alternative_corridor',
  response: BackendRouteCalculationResponse,
  origin: LocationPoint,
  destination: LocationPoint
): RouteAlternative {
  const isFastest = variant === 'estimated_fastest';
  const isShortest = variant === 'shortest';
  const leafletCoords = convertGeoJSONToLeafletCoords(
    backendRoute.geometry?.coordinates ?? []
  );

  const distanceKm = backendRoute.distance_km;
  const durationMinutes = backendRoute.estimated_duration_min;
  const merged = backendRoute.merged_route_types ?? [variant];
  const satisfiesBoth =
    merged.includes('estimated_fastest') && merged.includes('shortest');

  const routeName = satisfiesBoth
    ? 'Optimal Dominant Route (Fastest & Shortest)'
    : isFastest
      ? 'Estimated Fastest Route (Imputed Speeds)'
      : isShortest
        ? 'Shortest Distance Route (Graph Length)'
        : 'Alternative Highland Corridor (Secondary Path)';

  const routeId =
    variant === 'estimated_fastest'
      ? 'route-estimated-fastest'
      : variant === 'shortest'
        ? 'route-shortest'
        : 'route-alternative-corridor';

  const formattedDur = formatDurationHoursMinutes(durationMinutes);

  return {
    id: routeId,
    name: routeName,
    via: isFastest
      ? `Optimized by imputed travel_time · ${backendRoute.num_nodes} road nodes`
      : isShortest
        ? `Optimized by edge length · ${backendRoute.num_nodes} road nodes`
        : `Secondary corridor avoiding primary interior segments · ${backendRoute.num_nodes} road nodes`,
    status: isFastest ? 'RECOMMENDED' : 'ALTERNATIVE',
    distanceKm,
    durationMinutes,
    disasterRiskScore: 0,
    weatherRiskScore: 0,
    terrainExposureScore: 0,
    accessibilityScore: 100,
    logisticsScore: 100,
    warnings: backendRoute.estimation_limitations ?? [
      'Travel time is a static estimate from imputed road-class speeds (not live traffic)',
    ],
    tradeoffs: isFastest
      ? `Minimizes estimated transit time (${formattedDur} est. over ${distanceKm} km, ${backendRoute.num_nodes} nodes) using pre-imputed mountain highway speeds.`
      : isShortest
        ? `Minimizes total physical road distance (${distanceKm} km, ${formattedDur} est., ${backendRoute.num_nodes} nodes) across the OSMnx road graph.`
        : `Provides a distinct secondary road corridor (${distanceKm} km, ${formattedDur} est., ${backendRoute.num_nodes} nodes) for contingency routing.`,
    coordinates: leafletCoords,
    color: isFastest ? '#2563eb' : isShortest ? '#d97706' : '#0d9488',
    source:
      backendRoute.data_provenance ??
      `FastAPI + OSMnx GraphML Engine (${response.region_info?.graph_file ?? 'shillong_roads_clean.graphml'})`,
    isSimulated: false,
    routeType: variant,
    optimizationWeight:
      variant === 'estimated_fastest'
        ? 'travel_time'
        : variant === 'shortest'
          ? 'length'
          : 'penalized_travel_time',
    numNodes: backendRoute.num_nodes,
    nodeIds: backendRoute.node_ids,
    originSnap: response.origin,
    destinationSnap: response.destination,
    durationIsEstimate: backendRoute.duration_is_estimate,
    durationEstimateNote: backendRoute.duration_estimate_note,
    dataProvenance: backendRoute.data_provenance,
    estimationLimitations: backendRoute.estimation_limitations,
    mergedRouteTypes: backendRoute.merged_route_types,
    travelTimeDisclaimer: response.travel_time_disclaimer,
    edgeSummary: backendRoute.edge_summary,
    mlRanking: response.ml_ranking,
    elevationProfile: {
      minMeters: Math.min(origin.elevationMeters, destination.elevationMeters),
      maxMeters: Math.max(origin.elevationMeters, destination.elevationMeters),
      ascentMeters: Math.abs(origin.elevationMeters - destination.elevationMeters),
    },
  };
}

/**
 * Calls the FastAPI backend `POST /api/routes` endpoint to compute deduplicated
 * candidate routes on the processed OSMnx road graph, then deterministically
 * scores and ranks them according to the user's preference.
 */
export async function calculateRouteAlternatives(
  origin: LocationPoint,
  destination: LocationPoint,
  preference: RoutePreference = 'balanced',
  priority: PriorityType = 'Normal'
): Promise<RouteAlternative[]> {
  const baseUrl = getApiBaseUrl();
  const endpoint = `${baseUrl}/api/routes`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        origin: {
          lat: origin.lat,
          lng: origin.lng,
        },
        destination: {
          lat: destination.lat,
          lng: destination.lng,
        },
      }),
      signal: controller.signal,
    });
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    const isAbort = err instanceof DOMException && err.name === 'AbortError';
    throw new RouteApiError(
      'network_error',
      isAbort ? 'Route API Request Timed Out' : 'Backend Route API Unreachable',
      isAbort
        ? `Request to ${endpoint} timed out after 15 seconds.`
        : `Could not connect to the FastAPI route server at ${endpoint}. Ensure Uvicorn is running on ${baseUrl}.`,
      null
    );
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let errorCode: RouteErrorCode = 'api_error';
    let detailMessage = `Route calculation failed with HTTP ${response.status}.`;

    try {
      const errBody = await response.json();
      if (typeof errBody?.error === 'string') {
        if (
          errBody.error === 'out_of_coverage' ||
          errBody.error === 'invalid_coordinates' ||
          errBody.error === 'unreachable_destination' ||
          errBody.error === 'graph_unavailable'
        ) {
          errorCode = errBody.error;
        }
      }
      if (typeof errBody?.detail === 'string' && errBody.detail.trim().length > 0) {
        detailMessage = errBody.detail;
      }
    } catch {
      // Response body was not JSON
    }

    const titleMap: Record<RouteErrorCode, string> = {
      out_of_coverage: 'Location Outside Installed Regional Road Graph (3,000 m Limit)',
      invalid_coordinates: 'Invalid Origin or Destination Coordinates',
      unreachable_destination: 'Destination Unreachable in Road Network',
      graph_unavailable: 'Processed Road Graph Unavailable',
      network_error: 'Backend Route API Unreachable',
      api_error: 'Route Calculation Error',
    };

    throw new RouteApiError(
      errorCode,
      titleMap[errorCode],
      detailMessage,
      response.status
    );
  }

  const data = (await response.json()) as BackendRouteCalculationResponse;

  if (!data?.routes?.shortest || !data?.routes?.estimated_fastest) {
    throw new RouteApiError(
      'api_error',
      'Unexpected API Response Schema',
      'The backend response did not include both shortest and estimated_fastest routes.',
      response.status
    );
  }

  // Use deduplicated alternatives from backend when present; otherwise deduplicate client-side
  const rawList: BackendSingleRoute[] =
    Array.isArray(data.alternatives) && data.alternatives.length > 0
      ? data.alternatives
      : [
          data.routes.estimated_fastest,
          data.routes.shortest,
          ...(data.routes.alternative_corridor
            ? [data.routes.alternative_corridor]
            : []),
        ];

  const seenNodeKeys = new Set<string>();
  const builtAlternatives: RouteAlternative[] = [];
  for (const r of rawList) {
    const nodeKey = Array.isArray(r.node_ids) ? r.node_ids.join(',') : r.route_type;
    if (seenNodeKeys.has(nodeKey)) {
      continue;
    }
    seenNodeKeys.add(nodeKey);
    const variant =
      r.route_type === 'shortest'
        ? 'shortest'
        : r.route_type === 'alternative_corridor'
          ? 'alternative_corridor'
          : 'estimated_fastest';
    builtAlternatives.push(
      buildRouteAlternative(r, variant, data, origin, destination)
    );
  }

  return evaluateAndRankRoutes(builtAlternatives, preference, priority);
}
