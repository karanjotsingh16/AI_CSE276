/**
 * Client service for Alerts & Notifications System (Module G).
 */

import {
  AppNotification,
  NotificationCategory,
  NotificationSeverity,
  NotificationChannelsResponse,
} from '../types/notification';
import { getApiBaseUrl } from './routeService';

export async function fetchNotifications(
  unreadOnly: boolean = false,
  category?: NotificationCategory,
  severity?: NotificationSeverity
): Promise<{ count: number; unread_count: number; alerts: AppNotification[] }> {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();
  if (unreadOnly) params.append('unread_only', 'true');
  if (category) params.append('category', category);
  if (severity) params.append('severity', severity);

  const url = `${baseUrl}/api/notifications${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`Failed to fetch notifications (${response.status})`);
  }
  return response.json();
}

export async function fetchUnreadCount(): Promise<number> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/notifications/unread-count`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    return 0;
  }
  const data = await response.json();
  return data.unread_count ?? 0;
}

export async function markNotificationRead(
  alertId: string,
  isRead: boolean = true
): Promise<AppNotification> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/notifications/${alertId}/read`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ is_read: isRead }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update notification read status (${response.status})`);
  }
  const data = await response.json();
  return data.alert;
}

export async function markAllNotificationsRead(): Promise<number> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/notifications/mark-all-read`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to mark all notifications read (${response.status})`);
  }
  const data = await response.json();
  return data.marked_count ?? 0;
}

export async function syncNotificationTriggers(): Promise<number> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/notifications/sync-triggers`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    return 0;
  }
  const data = await response.json();
  return data.sync_result?.created_count ?? 0;
}

export async function fetchNotificationChannels(): Promise<NotificationChannelsResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/notifications/channels`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch notification channels (${response.status})`);
  }
  return response.json();
}

