export type RouteStatus = 'RECOMMENDED' | 'ALTERNATIVE' | 'NOT RECOMMENDED';

export type RoutePreference = 'shortest' | 'fastest' | 'balanced' | 'accessibility';

export interface PreferenceWeightConfig {
  preference: RoutePreference;
  label: string;
  shortLabel: string;
  distanceWeight: number;
  timeWeight: number;
  hierarchyWeight: number;
  formulaText: string;
  description: string;
}

export interface UnavailableMetricInfo {
  name: string;
  status: 'Unavailable in backend dataset';
  requiredData: string;
}

export interface RoadClassBreakdownPct {
  major_arterial: number;
  secondary_collector: number;
  local_unclassified: number;
}

export interface BackendEdgeSummary {
  total_edges: number;
  road_hierarchy_score: number;
  road_class_breakdown_pct: RoadClassBreakdownPct;
  highway_length_m_by_class?: Record<string, number>;
  imputed_speed_edges_pct: number;
  imputed_highway_edges_count?: number;
  bridges_count: number;
  tunnels_count: number;
  bridge_tunnel_edges_pct?: number;
}

export interface BackendMlRankingInfo {
  status: string;
  is_synthetic_benchmark: boolean;
  used_for_primary_recommendation: boolean;
  model_id: string;
  provenance_warning: string;
  predicted_ranking: string[];
  win_probabilities: Record<string, number>;
  agreement_with_deterministic_baseline: boolean;
}

export interface RouteEvaluationBreakdown {
  routeId: string;
  preference: RoutePreference;
  distanceScore: number;            // 0-100 (100 * d_min / d_i)
  timeScore: number;                // 0-100 (100 * t_min / t_i)
  roadHierarchyScore: number;       // 0-100 (length-weighted highway design speed quality)
  snapQualityScore: number;         // 0-100 (100 * (1 - (d_orig + d_dest) / (2 * d_max)))
  weightedScore: number;            // 0-100 (w_d * S_d + w_t * S_t + w_h * S_h)
  distanceWeight: number;
  timeWeight: number;
  hierarchyWeight: number;
  formulaText: string;
  minDistanceKm: number;
  minDurationMin: number;
  distanceDeltaKm: number;          // Difference vs. best distance (>= 0)
  durationDeltaMin: number;         // Difference vs. best duration (>= 0)
  vsAlternativeDistanceKm: number;  // Signed difference vs. the other candidate route
  vsAlternativeDurationMin: number; // Signed difference vs. the other candidate route
  impliedAvgSpeedKmh: number;
  intersectionDensityPerKm: number;
  roadClassBreakdownPct: RoadClassBreakdownPct;
  imputedSpeedEdgesPct: number;
  bridgesCount: number;
  tunnelsCount: number;
  routesAreIdentical: boolean;
  reasons: string[];
  advantages: string[];
  disadvantages: string[];
  tradeoffNote: string;
  algorithmDisclosure: string;
  unavailableMetrics: UnavailableMetricInfo[];
  mlRanking?: BackendMlRankingInfo;
}

export interface BackendSnapInfo {
  label: string;
  query_lat: number;
  query_lng: number;
  node_id: number;
  node_lat: number;
  node_lng: number;
  snap_distance_m: number;
}

export interface BackendGeoJSONLineString {
  type: 'LineString';
  coordinates: [number, number][]; // [longitude, latitude]
}

export interface BackendSingleRoute {
  route_type: 'shortest' | 'estimated_fastest' | 'alternative_corridor' | string;
  optimization_weight: 'length' | 'travel_time' | 'penalized_travel_time' | string;
  node_ids: number[];
  num_nodes: number;
  distance_km: number;
  estimated_duration_min: number;
  duration_is_estimate: boolean;
  duration_estimate_note: string;
  data_provenance?: string;
  estimation_limitations?: string[];
  merged_route_types?: string[];
  edge_summary?: BackendEdgeSummary;
  geometry: BackendGeoJSONLineString;
}

export interface BackendRouteCalculationResponse {
  origin: BackendSnapInfo;
  destination: BackendSnapInfo;
  max_snap_distance_m: number;
  travel_time_disclaimer: string;
  region_info?: {
    region_id: string;
    region_name: string;
    graph_file: string;
    nodes: number;
    directed_edges: number;
  };
  routes: {
    shortest: BackendSingleRoute;
    estimated_fastest: BackendSingleRoute;
    alternative_corridor?: BackendSingleRoute;
  };
  alternatives?: BackendSingleRoute[];
  evaluation?: Record<string, unknown>;
  ml_ranking?: BackendMlRankingInfo;
}

export type RouteErrorCode =
  | 'out_of_coverage'
  | 'invalid_coordinates'
  | 'unreachable_destination'
  | 'graph_unavailable'
  | 'network_error'
  | 'api_error';

export interface RouteErrorState {
  code: RouteErrorCode;
  title: string;
  detail: string;
  status?: number | null;
}

export interface RouteAlternative {
  id: string;
  name: string;
  via: string;
  status: RouteStatus;
  distanceKm: number;
  durationMinutes: number;
  disasterRiskScore: number;
  weatherRiskScore: number;
  terrainExposureScore: number;
  accessibilityScore: number;
  logisticsScore: number;        // 0-100 deterministic preference-weighted score
  warnings: string[];
  tradeoffs: string;
  coordinates: [number, number][]; // [lat, lng] array for Leaflet converted from GeoJSON [lng, lat]
  color: string;
  source: string;
  isSimulated: boolean;
  routeType?: 'shortest' | 'estimated_fastest' | 'alternative_corridor';
  optimizationWeight?: 'length' | 'travel_time' | 'penalized_travel_time';
  numNodes?: number;
  nodeIds?: number[];
  originSnap?: BackendSnapInfo;
  destinationSnap?: BackendSnapInfo;
  durationIsEstimate?: boolean;
  durationEstimateNote?: string;
  dataProvenance?: string;
  estimationLimitations?: string[];
  mergedRouteTypes?: string[];
  travelTimeDisclaimer?: string;
  edgeSummary?: BackendEdgeSummary;
  mlRanking?: BackendMlRankingInfo;
  elevationProfile?: { minMeters: number; maxMeters: number; ascentMeters: number };
  evaluation?: RouteEvaluationBreakdown;
}

export interface RouteCalculationSummary {
  origin: string;
  destination: string;
  primaryRouteId: string;
  routes: RouteAlternative[];
  source: 'FastAPI OSMnx GraphML Engine';
}
