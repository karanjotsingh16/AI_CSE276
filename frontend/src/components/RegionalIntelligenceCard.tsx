import React from 'react';
import { AlertCircle, Activity, CloudRain, Navigation } from 'lucide-react';
import { RouteAlternative } from '../types/route';
import { WeatherData } from '../types/weather';
import { DisasterAlert } from '../types/alert';

interface RegionalIntelligenceCardProps {
  selectedRoute: RouteAlternative | null;
  weather: WeatherData;
  alerts: DisasterAlert[];
  isLoading?: boolean;
}

export const RegionalIntelligenceCard: React.FC<RegionalIntelligenceCardProps> = ({
  selectedRoute,
  weather,
  alerts,
  isLoading
}) => {
  const relevantAlertsCount = alerts.filter(a => a.intersectsRoute !== false).length;
  const routeRiskScore = selectedRoute?.disasterRiskScore ?? null;
  const weatherRiskScore = weather.weatherRiskScore;
  const accessibilityScore = selectedRoute?.accessibilityScore ?? null;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-300 p-4 text-slate-800">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-base shadow-2xs">
            📊
          </div>
          <div>
            <h2 className="text-[14px] font-bold text-slate-900 leading-none">Regional Intelligence</h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Modelled Telemetry HUD</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60 text-[10px] font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>SYNCED</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        {/* Metric 1: Active Alerts */}
        <div className={`p-3 rounded-xl border transition-all duration-200 flex flex-col justify-between ${
          relevantAlertsCount > 0
            ? 'bg-gradient-to-br from-red-50 to-orange-50/60 border-red-200/80 shadow-2xs'
            : 'bg-slate-50/70 border-slate-200/70'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight">Active Alerts</span>
            <span className={`p-1 rounded-md ${relevantAlertsCount > 0 ? 'bg-red-500 text-white animate-pulse' : 'bg-slate-200 text-slate-400'}`}>
              <AlertCircle className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className={`text-2xl font-black ${relevantAlertsCount > 0 ? 'text-red-600' : 'text-slate-800'}`}>
              {alerts.length === 0 ? 'N/A' : relevantAlertsCount}
            </span>
            <span className="text-[10px] font-bold text-slate-400">Notices</span>
          </div>
          <div className="mt-1.5">
            <div className="w-full bg-slate-200/70 h-1.5 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${relevantAlertsCount > 0 ? 'bg-red-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.min(100, (relevantAlertsCount / 3) * 100 || 5)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Metric 2: Route Risk */}
        <div className="p-3 rounded-xl border border-slate-200/70 bg-slate-50/70 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight">Route Risk</span>
            <span className="p-1 rounded-md bg-blue-100 text-blue-600">
              <Activity className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black text-slate-800">
              {routeRiskScore !== null ? routeRiskScore : 'N/A'}
            </span>
            <span className="text-[10px] font-bold text-slate-400">/100</span>
          </div>
          <div className="mt-1.5">
            <div className="w-full bg-slate-200/70 h-1.5 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  routeRiskScore && routeRiskScore > 50 ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${routeRiskScore || 0}%` }}
              />
            </div>
          </div>
        </div>

        {/* Metric 3: Weather Risk */}
        <div className="p-3 rounded-xl border border-slate-200/70 bg-slate-50/70 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight">Weather Risk</span>
            <span className="p-1 rounded-md bg-sky-100 text-sky-600">
              <CloudRain className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black text-slate-800">
              {weather.state === 'loading' ? '...' : weatherRiskScore !== null ? weatherRiskScore : 'N/A'}
            </span>
            <span className="text-[10px] font-bold text-slate-400">/100</span>
          </div>
          <div className="mt-1.5">
            <div className="w-full bg-slate-200/70 h-1.5 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  weatherRiskScore && weatherRiskScore > 50 ? 'bg-amber-500' : 'bg-sky-500'
                }`}
                style={{ width: `${weatherRiskScore || 0}%` }}
              />
            </div>
          </div>
        </div>

        {/* Metric 4: Accessibility */}
        <div className="p-3 rounded-xl border border-slate-200/70 bg-slate-50/70 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight">Accessibility</span>
            <span className="p-1 rounded-md bg-teal-100 text-teal-600">
              <Navigation className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black text-slate-800">
              {accessibilityScore !== null ? accessibilityScore : 'N/A'}
            </span>
            <span className="text-[10px] font-bold text-slate-400">/100</span>
          </div>
          <div className="mt-1.5">
            <div className="w-full bg-slate-200/70 h-1.5 rounded-full overflow-hidden">
              <div
                className="h-full bg-teal-500 rounded-full transition-all duration-500"
                style={{ width: `${accessibilityScore || 0}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
