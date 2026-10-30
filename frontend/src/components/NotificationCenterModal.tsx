import React, { useState, useEffect, useCallback } from 'react';
import {
  Bell,
  X,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  CloudRain,
  Truck,
  CheckCheck,
  Radio,
  MapPin,
  RefreshCw,
} from 'lucide-react';
import { AppNotification, NotificationChannel } from '../types/notification';
import {
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  syncNotificationTriggers,
  fetchNotificationChannels,
} from '../services/notificationService';

interface NotificationCenterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFocusLocation?: (coords: [number, number]) => void;
  onUnreadCountChange?: (count: number) => void;
}

export const NotificationCenterModal: React.FC<NotificationCenterModalProps> = ({
  isOpen,
  onClose,
  onFocusLocation,
  onUnreadCountChange,
}) => {
  const [activeFilter, setActiveFilter] = useState<'all' | 'unread' | 'critical' | 'channels'>('all');
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [channelsDisclaimer, setChannelsDisclaimer] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  const loadNotifications = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetchNotifications(
        activeFilter === 'unread',
        undefined,
        activeFilter === 'critical' ? 'critical' : undefined
      );
      setNotifications(res.alerts);
      setUnreadCount(res.unread_count);
      if (onUnreadCountChange) {
        onUnreadCountChange(res.unread_count);
      }
    } catch (err) {
      console.error('Error fetching notifications:', err);
    } finally {
      setIsLoading(false);
    }
  }, [activeFilter, onUnreadCountChange]);

  const loadChannels = useCallback(async () => {
    try {
      const res = await fetchNotificationChannels();
      setChannels(res.channels);
      setChannelsDisclaimer(res.disclaimer);
    } catch (err) {
      console.error('Error fetching notification channels:', err);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadNotifications();
      loadChannels();
    }
  }, [isOpen, loadNotifications, loadChannels]);

  const handleToggleRead = async (alertId: string, currentRead: boolean) => {
    try {
      await markNotificationRead(alertId, !currentRead);
      loadNotifications();
    } catch (err) {
      console.error('Error toggling read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      loadNotifications();
    } catch (err) {
      console.error('Error marking all read:', err);
    }
  };

  const handleSyncTriggers = async () => {
    setIsSyncing(true);
    try {
      await syncNotificationTriggers();
      await loadNotifications();
    } catch (err) {
      console.error('Error syncing triggers:', err);
    } finally {
      setIsSyncing(false);
    }
  };

  if (!isOpen) return null;

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'road_closure':
        return <AlertOctagon className="w-4 h-4 text-rose-600" />;
      case 'landslide':
      case 'flood':
        return <AlertTriangle className="w-4 h-4 text-amber-600" />;
      case 'severe_weather':
        return <CloudRain className="w-4 h-4 text-sky-600" />;
      case 'route_deviation':
      case 'vehicle_delay':
        return <Truck className="w-4 h-4 text-indigo-600" />;
      default:
        return <Radio className="w-4 h-4 text-slate-500" />;
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-100 text-rose-800 border border-rose-200 uppercase">
            CRITICAL
          </span>
        );
      case 'severe':
        return (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-100 text-amber-800 border border-amber-200 uppercase">
            SEVERE
          </span>
        );
      case 'warning':
        return (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-yellow-100 text-yellow-800 border border-yellow-200 uppercase">
            WARNING
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-sky-100 text-sky-800 border border-sky-200 uppercase">
            INFO
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-[2200] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl max-h-[88vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="relative w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 text-white font-mono text-[9px] font-bold flex items-center justify-center ring-2 ring-slate-900">
                  {unreadCount}
                </span>
              )}
            </div>
            <div>
              <h2 className="text-sm font-semibold tracking-wide">
                Operational Alerts & Notification Center
              </h2>
              <p className="text-[11px] text-slate-300">
                Automated multi-hazard triggers with zero-duplicate protection (Module G)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            type="button"
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Toolbar & Filters */}
        <div className="px-6 py-3 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                activeFilter === 'all'
                  ? 'bg-slate-900 text-white'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              All Alerts
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('unread')}
              className={`px-3 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                activeFilter === 'unread'
                  ? 'bg-slate-900 text-white'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              Unread ({unreadCount})
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('critical')}
              className={`px-3 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                activeFilter === 'critical'
                  ? 'bg-slate-900 text-white'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              Critical / Severe
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('channels')}
              className={`px-3 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                activeFilter === 'channels'
                  ? 'bg-slate-900 text-white'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              Channels & Gateways
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={isSyncing}
              onClick={handleSyncTriggers}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 font-medium cursor-pointer"
              title="Evaluate live modules and generate deduplicated alerts"
            >
              <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin text-sky-600' : ''}`} />
              <span>{isSyncing ? 'Syncing...' : 'Sync Triggers'}</span>
            </button>
            <button
              type="button"
              onClick={handleMarkAllRead}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 font-medium cursor-pointer"
            >
              <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Mark All Read</span>
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-3 flex-1 text-xs">
          {activeFilter === 'channels' ? (
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 space-y-1">
                <h4 className="font-semibold text-slate-900">Notification Channel Architecture</h4>
                <p className="text-[11px] text-slate-500">
                  Built on an extensible channel abstraction. Real notifications are currently broadcasted
                  through the in-app notification center and real-time map overlay.
                </p>
              </div>

              <div className="space-y-2">
                {channels.map((ch) => (
                  <div
                    key={ch.channel_id}
                    className="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <h5 className="font-semibold text-slate-900">{ch.name}</h5>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${
                          ch.status === 'active_operational'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {ch.status.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600">{ch.description}</p>
                  </div>
                ))}
              </div>

              {channelsDisclaimer && (
                <div className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-2.5 leading-snug">
                  <strong>Academic Integrity Notice:</strong> {channelsDisclaimer}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2.5">
              {notifications.length === 0 ? (
                <div className="py-12 text-center text-slate-400">
                  <CheckCircle2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p>No alerts matching this filter.</p>
                </div>
              ) : (
                notifications.map((alt) => (
                  <div
                    key={alt.alert_id}
                    className={`p-3.5 rounded-xl border transition-all space-y-2 ${
                      !alt.is_read
                        ? 'bg-white border-slate-300 shadow-xs ring-1 ring-slate-900/5'
                        : 'bg-slate-50/60 border-slate-200/80 text-slate-500'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2.5">
                        <div className="mt-0.5 shrink-0">{getCategoryIcon(alt.category)}</div>
                        <div className="space-y-0.5">
                          <h4
                            className={`font-semibold leading-tight ${
                              !alt.is_read ? 'text-slate-900' : 'text-slate-700'
                            }`}
                          >
                            {alt.title}
                          </h4>
                          <p className="text-[10px] text-slate-400">
                            Source: <span className="font-medium text-slate-600">{alt.source}</span>
                            {alt.district ? ` • ${alt.district}` : ''}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {getSeverityBadge(alt.severity)}
                      </div>
                    </div>

                    <p
                      className={`text-[11px] leading-relaxed ${
                        !alt.is_read ? 'text-slate-700' : 'text-slate-500'
                      }`}
                    >
                      {alt.message}
                    </p>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-100">
                      <span>{new Date(alt.created_at).toLocaleString()}</span>
                      <div className="flex items-center gap-2">
                        {alt.latitude !== null && alt.longitude !== null && onFocusLocation && (
                          <button
                            type="button"
                            onClick={() => {
                              onFocusLocation([alt.latitude!, alt.longitude!]);
                              onClose();
                            }}
                            className="text-sky-600 hover:text-sky-800 font-medium inline-flex items-center gap-0.5 cursor-pointer"
                          >
                            <MapPin className="w-3 h-3" /> Focus Map
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleToggleRead(alt.alert_id, alt.is_read)}
                          className="text-slate-500 hover:text-slate-800 font-medium cursor-pointer"
                        >
                          {alt.is_read ? 'Mark Unread' : 'Mark as Read'}
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
