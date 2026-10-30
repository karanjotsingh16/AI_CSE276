import {
  DemandZonesResponse,
  DemandZoneErrorState
} from '../types/demandZone';
import { getApiBaseUrl } from './routeService';

export class DemandZoneApiError extends Error {
  public readonly code: DemandZoneErrorState['code'];
  public readonly title: string;
  public readonly detail: string;
  public readonly status: number | null;

  constructor(
    code: DemandZoneErrorState['code'],
    title: string,
    detail: string,
    status: number | null = null
  ) {
    super(detail);
    this.name = 'DemandZoneApiError';
    this.code = code;
    this.title = title;
    this.detail = detail;
    this.status = status;
  }
}

/**
 * Calls the local FastAPI K-Means demand-zone endpoint (`POST /api/demand-zones`).
 * Never fabricates fallback cluster centres, point assignments, or evaluation metrics.
 */
export async function fetchDemandZones(
  nClusters: number = 4,
  randomState: number = 42
): Promise<DemandZonesResponse> {
  const baseUrl = getApiBaseUrl();
  const endpoint = `${baseUrl}/api/demand-zones`;

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      body: JSON.stringify({
        n_clusters: nClusters,
        random_state: randomState
      })
    });
  } catch (networkErr: unknown) {
    const rawMsg =
      networkErr instanceof Error ? networkErr.message : 'Network connection failed';
    throw new DemandZoneApiError(
      'network_error',
      'Demand Clustering API Unreachable',
      `Could not connect to FastAPI demand-zones service at ${endpoint} (${rawMsg}). Ensure uvicorn is running on ${baseUrl}.`,
      null
    );
  }

  if (!response.ok) {
    let errorCode = 'api_error';
    let errorDetail = `Backend returned HTTP ${response.status} (${response.statusText}).`;

    try {
      const errBody = await response.json();
      if (errBody && typeof errBody === 'object') {
        if (typeof errBody.error === 'string') {
          errorCode = errBody.error;
        }
        if (typeof errBody.detail === 'string') {
          errorDetail = errBody.detail;
        } else if (Array.isArray(errBody.detail)) {
          errorDetail = errBody.detail
            .map((e: { msg?: string }) => e.msg || JSON.stringify(e))
            .join('; ');
        }
      }
    } catch {
      // Non-JSON error body
    }

    if (
      response.status === 422 ||
      errorCode === 'invalid_cluster_configuration' ||
      errorCode === 'insufficient_demand_points' ||
      errorCode === 'invalid_demand_record' ||
      errorCode === 'empty_demand_dataset'
    ) {
      throw new DemandZoneApiError(
        'invalid_parameters',
        'Invalid Cluster Parameters',
        errorDetail,
        response.status
      );
    }

    if (response.status === 503 || errorCode === 'demand_dataset_unavailable') {
      throw new DemandZoneApiError(
        'service_unavailable',
        'Demand Dataset Unavailable',
        errorDetail,
        response.status
      );
    }

    throw new DemandZoneApiError(
      'api_error',
      `Demand Clustering Error (HTTP ${response.status})`,
      errorDetail,
      response.status
    );
  }

  const data: DemandZonesResponse = await response.json();

  if (!data || !Array.isArray(data.clusters) || !Array.isArray(data.points)) {
    throw new DemandZoneApiError(
      'api_error',
      'Malformed Demand-Zones Response',
      'FastAPI response did not contain valid clusters and points arrays.',
      response.status
    );
  }

  return data;
}

