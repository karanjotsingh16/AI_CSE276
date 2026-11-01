import React from 'react';
import { ExternalLink, ShieldAlert, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { DisasterAlert, AlertSourceState } from '../../types/alert';
import { formatTimestamp } from '../../logic/formatters';

interface DisasterAlertsCardProps {
  alerts: DisasterAlert[];
  state: AlertSourceState;
  stateMessage: string;
  sourceUrl: string;
  onRefresh: () => void;
  isLoading?: boolean;
}

export const DisasterAlertsCard: React.FC<DisasterAlertsCardProps> = ({
  alerts,
  state,
  sourceUrl,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-300 p-4 text-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-red-50 text-red-600 flex items-center justify-center font-bold text-base shadow-2xs">
            🚨
          </div>
          <div>
            <h2 className="text-[14px] font-bold text-slate-900 leading-none">Disaster Alerts</h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-medium">NDMA / SACHET CAP Feed</p>
          </div>
        </div>
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[11px] font-bold text-blue-600 hover:text-blue-800 transition-colors"
        >
          <span>SACHET Portal</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {alerts.length === 0 ? (
        <div className="py-4 text-center bg-slate-50 rounded-xl border border-slate-100 text-slate-500 text-xs flex items-center justify-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          <span className="font-medium">No active disaster alerts intersecting this corridor.</span>
        </div>
      ) : (
        <div className="space-y-2.5">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-3 rounded-xl border-l-4 transition-all duration-200 text-left text-xs ${
                alert.intersectsRoute === true
                  ? 'bg-amber-50/50 border-l-amber-500 border border-amber-200 shadow-2xs'
                  : 'bg-white border-l-slate-400 border border-slate-200'
              }`}
            >
              <div className="flex items-start justify-between gap-1.5 mb-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping shrink-0" />
                  <h4 className="font-bold text-slate-900 leading-snug">{alert.title}</h4>
                </div>
                <span className="text-[9px] font-black px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 uppercase tracking-wider shrink-0">
                  {alert.severity}
                </span>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1.5 font-medium">
                <span>{alert.issuingAgency.split('/')[0]}</span>
                <span>{alert.affectedRegion.split('(')[0]}</span>
              </div>

              <p className="text-[11px] text-slate-600 leading-snug mb-2 font-normal">
                {alert.description}
              </p>

              <div className="flex items-center justify-between pt-1.5 border-t border-slate-100/80 text-[10px]">
                <span className={`font-bold flex items-center gap-1 ${alert.intersectsRoute ? 'text-amber-700' : 'text-slate-500'}`}>
                  <AlertTriangle className="w-3 h-3 text-amber-600" />
                  {alert.intersectsRoute ? 'Intersects active delivery route' : 'Regional notice'}
                </span>
                <a
                  href={alert.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-bold text-blue-600 hover:text-blue-800 flex items-center gap-0.5"
                >
                  Verify <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
