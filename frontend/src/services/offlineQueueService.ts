/**
 * Offline Field Operations & Incident Queue Service (Module H / Phase 7)
 *
 * Provides persistent local queueing for field incidents submitted while
 * traversing low-connectivity corridors in Meghalaya and North-East India.
 * Automatically synchronizes drafts to the FastAPI backend once cellular/WiFi returns.
 */

import { IncidentReportInput, IncidentReport } from '../types/accessibility';
import { submitIncidentReport } from './accessibilityService';

export interface OfflineDraft {
  draftId: string;
  queuedAt: string;
  payload: IncidentReportInput;
  attempts: number;
  lastError?: string;
}

export interface SyncResult {
  syncedCount: number;
  failedCount: number;
  syncedReports: IncidentReport[];
  errors: string[];
}

const STORAGE_KEY = 'ner_smartroute_offline_reports_queue_v1';

type QueueChangeListener = (queue: OfflineDraft[]) => void;
const listeners: Set<QueueChangeListener> = new Set();

function notifyListeners(queue: OfflineDraft[]) {
  listeners.forEach((listener) => {
    try {
      listener(queue);
    } catch {
      // Ignore listener error
    }
  });
}

export function getOfflineDrafts(): OfflineDraft[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveOfflineDrafts(drafts: OfflineDraft[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts));
    notifyListeners(drafts);
  } catch (err) {
    console.error('Failed to save offline drafts to localStorage:', err);
  }
}

export function queueIncidentDraft(payload: IncidentReportInput): OfflineDraft {
  const drafts = getOfflineDrafts();
  const draftId = `draft_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  const newDraft: OfflineDraft = {
    draftId,
    queuedAt: new Date().toISOString(),
    payload,
    attempts: 0,
  };

  drafts.unshift(newDraft);
  saveOfflineDrafts(drafts);
  return newDraft;
}

export function removeOfflineDraft(draftId: string): void {
  const drafts = getOfflineDrafts().filter((d) => d.draftId !== draftId);
  saveOfflineDrafts(drafts);
}

export function clearOfflineQueue(): void {
  saveOfflineDrafts([]);
}

export async function syncOfflineDrafts(): Promise<SyncResult> {
  const drafts = getOfflineDrafts();
  if (drafts.length === 0) {
    return { syncedCount: 0, failedCount: 0, syncedReports: [], errors: [] };
  }

  const syncedReports: IncidentReport[] = [];
  const errors: string[] = [];
  const remainingDrafts: OfflineDraft[] = [];

  for (const draft of drafts) {
    try {
      const created = await submitIncidentReport(draft.payload);
      syncedReports.push(created);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      errors.push(`${draft.payload.title}: ${msg}`);
      remainingDrafts.push({
        ...draft,
        attempts: draft.attempts + 1,
        lastError: msg,
      });
    }
  }

  saveOfflineDrafts(remainingDrafts);

  return {
    syncedCount: syncedReports.length,
    failedCount: remainingDrafts.length,
    syncedReports,
    errors,
  };
}

export function subscribeToOfflineQueue(listener: QueueChangeListener): () => void {
  listeners.add(listener);
  // initial call
  listener(getOfflineDrafts());
  return () => {
    listeners.delete(listener);
  };
}

// Auto-sync listener when browser reconnects to internet
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    console.info('[NER SmartRoute] Network connection restored. Auto-syncing pending offline drafts...');
    syncOfflineDrafts().then((res) => {
      if (res.syncedCount > 0) {
        console.info(`[NER SmartRoute] Successfully synced ${res.syncedCount} queued reports.`);
      }
    });
  });
}

