/**
 * Client service for GPS Vehicle & Delivery Tracking (Module F).
 */

import {
  Vehicle,
  Delivery,
  DeliveryCreateInput,
  TelemetryResponse,
  DeliveryStatus,
} from '../types/tracking';
import { getApiBaseUrl } from './routeService';

export async function fetchVehicles(vehicleType?: string): Promise<Vehicle[]> {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (vehicleType) params.append('vehicle_type', vehicleType);

  const url = `${baseUrl}/api/tracking/vehicles${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`Failed to fetch vehicles (${response.status})`);
  }
  const data = await response.json();
  return data.vehicles ?? [];
}

export async function fetchDeliveries(
  status?: DeliveryStatus,
  vehicleId?: string
): Promise<Delivery[]> {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (vehicleId) params.append('vehicle_id', vehicleId);

  const url = `${baseUrl}/api/tracking/deliveries${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`Failed to fetch deliveries (${response.status})`);
  }
  const data = await response.json();
  return data.deliveries ?? [];
}

export async function createDelivery(
  payload: DeliveryCreateInput
): Promise<Delivery> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/tracking/deliveries`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Delivery creation failed (${response.status})`);
  }
  const data = await response.json();
  return data.delivery;
}

export async function stepSimulatedDelivery(
  deliveryId: string,
  progressStepPct: number = 5.0,
  simulateDeviation: boolean = false
): Promise<TelemetryResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/tracking/deliveries/${deliveryId}/simulate-step`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        progress_step_pct: progressStepPct,
        simulate_deviation: simulateDeviation,
      }),
    }
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Simulation step failed (${response.status})`);
  }
  return response.json();
}

export async function updateDeliveryStatus(
  deliveryId: string,
  newStatus: DeliveryStatus,
  delayReason?: string
): Promise<Delivery> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/tracking/deliveries/${deliveryId}/status`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        new_status: newStatus,
        delay_reason: delayReason,
      }),
    }
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Delivery status update failed (${response.status})`);
  }
  const data = await response.json();
  return data.delivery;
}
