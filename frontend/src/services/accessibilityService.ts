/**
 * Client service for Road Accessibility Monitoring (Module D)
 * and Field Incident Reporting (Module E).
 */

import {
  RoadSegment,
  IncidentReport,
  IncidentReportInput,
  IncidentReviewInput,
  AccessibilityAuditLog,
  SegmentStatus,
  IncidentStatus,
  IncidentType,
} from '../types/accessibility';
import { getApiBaseUrl } from './routeService';

export async function fetchRoadSegments(
  district?: string,
  status?: SegmentStatus
): Promise<RoadSegment[]> {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (district) params.append('district', district);
  if (status) params.append('status', status);

  const url = `${baseUrl}/api/accessibility/segments${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`Failed to fetch road segments (${response.status})`);
  }
  const data = await response.json();
  return data.segments ?? [];
}

export async function fetchIncidents(
  status?: IncidentStatus,
  incidentType?: IncidentType,
  district?: string
): Promise<IncidentReport[]> {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (incidentType) params.append('incident_type', incidentType);
  if (district) params.append('district', district);

  const url = `${baseUrl}/api/accessibility/incidents${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`Failed to fetch incident reports (${response.status})`);
  }
  const data = await response.json();
  return data.incidents ?? [];
}

export async function submitIncidentReport(
  payload: IncidentReportInput
): Promise<IncidentReport> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/accessibility/reports`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const detail = errorBody.detail || `Server responded with ${response.status}`;
    throw new Error(detail);
  }

  const data = await response.json();
  return data.incident;
}

export async function reviewIncident(
  reportId: string,
  review: IncidentReviewInput
): Promise<IncidentReport> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/accessibility/incidents/${reportId}/status`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(review),
    }
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const detail = errorBody.detail || `Server responded with ${response.status}`;
    throw new Error(detail);
  }

  const data = await response.json();
  return data.incident;
}

export async function fetchAuditLogs(
  limit: number = 50
): Promise<AccessibilityAuditLog[]> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/accessibility/audit-log?limit=${limit}`;
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`Failed to fetch accessibility audit trail (${response.status})`);
  }
  const data = await response.json();
  return data.logs ?? [];
}

export async function uploadIncidentPhoto(file: File): Promise<string> {
  const baseUrl = getApiBaseUrl();
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${baseUrl}/api/accessibility/upload-photo`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Photo upload failed with ${response.status}`);
  }

  const data = await response.json();
  return `${baseUrl}${data.photo_url}`;
}

