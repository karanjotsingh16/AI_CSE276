export type CoverageStatusType =
  | 'routable_in_loaded_graph'
  | 'routable_in_installed_region'
  | 'supported_region_not_downloaded'
  | 'outside_all_catalog_regions';

export interface GeocodeCoverageInfo {
  within_loaded_graph: boolean;
  within_india_network?: boolean;
  status: CoverageStatusType;
  region_id: string | null;
  region_name: string | null;
  nearest_node_id: number | null;
  nearest_node_lat: number | null;
  nearest_node_lng: number | null;
  snap_distance_m: number | null;
  max_snap_distance_m: number;
  matching_catalog_regions: string[];
  acquire_command: string | null;
  message: string;
}

export interface GeocodedLocationResult {
  place_id: string;
  name: string;
  display_name: string;
  state: string;
  district?: string;
  lat: number;
  lng: number;
  elevation_m?: number;
  place_type: string;
  source: string;
  description?: string;
  coverage: GeocodeCoverageInfo;
}

export interface GeocodeSearchResponse {
  query: string;
  geocoder_source: string;
  attribution: string;
  count: number;
  results: GeocodedLocationResult[];
}

export interface RegionalGraphInfo {
  region_id: string;
  name: string;
  state: string;
  phase: string;
  graph_filename: string;
  center_lat: number;
  center_lng: number;
  download_radius_m: number;
  bounds: {
    min_lat: number;
    max_lat: number;
    min_lng: number;
    max_lng: number;
  };
  key_hubs: string[];
  description: string;
  installed_on_disk: boolean;
  loaded_in_memory: boolean;
  graph_path: string | null;
  file_size_mb: number | null;
  nodes: number | null;
  directed_edges: number | null;
  acquire_cli_command: string;
}

export interface RegionsCatalogResponse {
  default_region_id: string;
  max_snap_distance_m: number;
  regions: RegionalGraphInfo[];
}

