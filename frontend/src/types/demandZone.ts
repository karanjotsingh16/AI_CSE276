/**
 * TypeScript interfaces matching the FastAPI `POST /api/demand-zones` contract
 * in `backend/main.py` (`DemandZonesResponse`).
 */

export interface DemandZoneDataProvenance {
  data_sources: string[];
  is_synthetic_demo: boolean;
  provenance_note: string;
}

export interface DemandZoneCoordinateProjection {
  input_crs: string;
  clustering_crs: string;
  clustering_units: string;
  explanation: string;
  limitations: string[];
}

export interface DemandZoneEvaluationMetrics {
  inertia_m2: number;
  silhouette_score: number | null;
  davies_bouldin_score: number | null;
  metrics_omitted_reason: string | null;
  interpretation_note: string;
}

export interface DemandClusterSummary {
  cluster_id: number;
  center_lat: number;
  center_lng: number;
  center_easting_m: number;
  center_northing_m: number;
  demand_weighted_center_lat: number;
  demand_weighted_center_lng: number;
  point_count: number;
  total_demand_units: number;
  mean_demand_units: number;
  demand_share_pct: number;
  demand_weighted_priority_index: number;
  priority_breakdown: Record<string, number>;
  mean_distance_to_center_m: number;
  max_distance_to_center_m: number;
}

export interface AssignedDemandPoint {
  point_index: number;
  latitude: number;
  longitude: number;
  demand_units: number;
  priority: string;
  priority_weight: number;
  data_source: string;
  cluster_id: number;
  easting_m: number;
  northing_m: number;
  distance_to_cluster_center_m: number;
}

export interface DemandZonesResponse {
  model: string;
  n_clusters: number;
  random_state: number;
  dataset_size: number;
  total_demand_units: number;
  data_provenance: DemandZoneDataProvenance;
  coordinate_projection: DemandZoneCoordinateProjection;
  evaluation_metrics: DemandZoneEvaluationMetrics;
  clusters: DemandClusterSummary[];
  points: AssignedDemandPoint[];
}

export interface DemandZoneErrorState {
  code: 'invalid_parameters' | 'service_unavailable' | 'network_error' | 'api_error';
  title: string;
  detail: string;
  status: number | null;
}

/**
 * Distinct colour palette for K-Means demand clusters (distinct from route blue/amber).
 */
export const DEMAND_CLUSTER_COLORS: readonly string[] = [
  '#8b5cf6', // Cluster 0: Violet
  '#0d9488', // Cluster 1: Teal
  '#ea580c', // Cluster 2: Orange
  '#db2777', // Cluster 3: Pink/Magenta
  '#4f46e5', // Cluster 4: Indigo
  '#16a34a', // Cluster 5: Green
  '#ca8a04', // Cluster 6: Dark Yellow
  '#0284c7'  // Cluster 7: Sky Blue
];

export function getClusterColor(clusterId: number): string {
  const index = Math.abs(clusterId) % DEMAND_CLUSTER_COLORS.length;
  return DEMAND_CLUSTER_COLORS[index];
}

