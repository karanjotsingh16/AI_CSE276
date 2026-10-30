import React, { useState, useEffect } from 'react';
import {
  X,
  Wifi,
  WifiOff,
  RefreshCw,
  Trash2,
  Clock,
  AlertTriangle,
  CheckCircle,
  FileText,
  ShieldCheck,
} from 'lucide-react';
import {
  OfflineDraft,
  syncOfflineDrafts,
  removeOfflineDraft,
  clearOfflineQueue,
  subscribeToOfflineQueue,
} from '../services/offlineQueueService';
import { useTranslation } from '../i18n';

interface OfflineQueueModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSyncComplete?: () => void;
}

export const OfflineQueueModal: React.FC<OfflineQueueModalProps> = ({
  isOpen,
  onClose,
  onSyncComplete,
}) => {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<OfflineDraft[]>([]);
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncFeedback, setSyncFeedback] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    const unsubscribe = subscribeToOfflineQueue((updated) => {
      setDrafts(updated);
    });

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      unsubscribe();
    };
  }, []);

  if (!isOpen) return null;

  const handleManualSync = async () => {
    if (drafts.length === 0) return;
    setIsSyncing(true);
    setSyncFeedback(null);
    try {
      const result = await syncOfflineDrafts();
      if (result.syncedCount > 0) {
        setSyncFeedback({
          success: true,
          message: `Successfully uploaded ${result.syncedCount} queued reports!`,
        });
        if (onSyncComplete) onSyncComplete();
      } else if (result.failedCount > 0) {
        setSyncFeedback({
          success: false,
          message: `Sync failed for ${result.failedCount} drafts. Check network or server connection.`,
        });
      }
    } catch (err: unknown) {
      setSyncFeedback({
        success: false,
        message: err instanceof Error ? err.message : 'Error syncing drafts',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRemoveDraft = (id: string) => {
    removeOfflineDraft(id);
  };

  const handleClearAll = () => {
    if (window.confirm('Discard all offline drafts? This action cannot be undone.')) {
      clearOfflineQueue();
      setDrafts([]);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center font-bold">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-800">
                  {t.syncQueue} (Offline Drafts)
                </h3>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
                    isOnline
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {isOnline ? (
                    <>
                      <Wifi className="w-3 h-3" /> {t.online}
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-3 h-3" /> {t.offline}
                    </>
                  )}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Meghalaya remote field operations queue (persistent storage)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Sync Feedback Alert */}
        {syncFeedback && (
          <div
            className={`px-5 py-2.5 text-xs font-medium flex items-center gap-2 border-b ${
              syncFeedback.success
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-rose-50 text-rose-800 border-rose-200'
            }`}
          >
            {syncFeedback.success ? (
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            )}
            <span>{syncFeedback.message}</span>
          </div>
        )}

        {/* Content Body */}
        <div className="p-5 overflow-y-auto flex-1 space-y-3.5">
          {drafts.length === 0 ? (
            <div className="text-center py-12 px-4">
              <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
                <CheckCircle className="w-6 h-6 text-emerald-500" />
              </div>
              <h4 className="text-sm font-semibold text-slate-700">Queue is Clear</h4>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                No offline drafts pending. Any incident reports submitted during network blackouts will automatically appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs text-slate-500 pb-1">
                <span>{drafts.length} reports waiting to synchronize</span>
                <button
                  onClick={handleClearAll}
                  className="text-rose-600 hover:text-rose-800 hover:underline flex items-center gap-1 font-medium"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Clear All
                </button>
              </div>

              {drafts.map((draft) => (
                <div
                  key={draft.draftId}
                  className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors flex items-start justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-800">
                        {draft.payload.title}
                      </span>
                      <span className="px-1.5 py-0.5 bg-slate-200 text-slate-700 rounded text-[10px] uppercase font-semibold">
                        {draft.payload.incident_type}
                      </span>
                      <span className="px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded text-[10px] font-semibold">
                        {draft.payload.severity}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 line-clamp-1">
                      {draft.payload.description}
                    </p>

                    <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-1">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(draft.queuedAt).toLocaleTimeString()}
                      </span>
                      <span>
                        Coords: {draft.payload.latitude.toFixed(4)}, {draft.payload.longitude.toFixed(4)}
                      </span>
                      {draft.attempts > 0 && (
                        <span className="text-rose-600 font-medium">
                          Failed attempts: {draft.attempts}
                        </span>
                      )}
                    </div>

                    {draft.lastError && (
                      <p className="text-[11px] text-rose-600 bg-rose-50 rounded p-1 mt-1">
                        {draft.lastError}
                      </p>
                    )}
                  </div>

                  <button
                    onClick={() => handleRemoveDraft(draft.draftId)}
                    title="Remove from queue"
                    className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Academic Integrity & Offline Resilience Note */}
          <div className="p-3 bg-amber-50/70 border border-amber-200/80 rounded-xl flex items-start gap-2.5 text-xs text-amber-900">
            <ShieldCheck className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-950">
                Offline Field Resilience Architecture
              </p>
              <p className="mt-0.5 text-amber-800 text-[11px] leading-relaxed">
                {t.offlineSyncReady}
              </p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-5 py-3.5 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200/60 rounded-xl transition-colors"
          >
            {t.close}
          </button>

          <button
            onClick={handleManualSync}
            disabled={drafts.length === 0 || isSyncing}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
              drafts.length === 0 || isSyncing
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm shadow-emerald-600/20'
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? 'Syncing...' : `${t.syncNow} (${drafts.length})`}
          </button>
        </div>
      </div>
    </div>
  );
};
