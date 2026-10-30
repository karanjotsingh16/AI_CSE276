import React from 'react';
import { RouteAlternative } from '../types/route';
import { DisasterAlert } from '../types/alert';
import { WeatherData } from '../types/weather';
import { assessRouteSafety } from '../logic/routeRisk';

interface RouteSafetyCardProps {
  selectedRoute: RouteAlternative | null;
  alerts: DisasterAlert[];
  weather: WeatherData;
}

export const RouteSafetyCard: React.FC<RouteSafetyCardProps> = ({
  selectedRoute,
  alerts,
  weather
}) => {
  const assessment = assessRouteSafety(selectedRoute, alerts, weather);
  const hasScore = assessment.overallRiskScore !== null && selectedRoute !== null;
  const score = assessment.overallRiskScore ?? 0;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-300 p-4 text-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center font-bold text-base shadow-2xs">
            🛡️
          </div>
          <div>
            <h2 className="text-[14px] font-bold text-slate-900 leading-none">Route Safety</h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Simulated Multi-Hazard Index</p>
          </div>
        </div>
        <span
          className={`text-[10px] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wider ${
            assessment.classification === 'LOW'
              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300/60'
              : assessment.classification === 'MODERATE'
              ? 'bg-amber-100 text-amber-800 border border-amber-300/60'
              : assessment.classification === 'HIGH'
              ? 'bg-red-100 text-red-800 border border-red-300/60'
              : 'bg-slate-100 text-slate-600 border border-slate-300/60'
          }`}
        >
          {assessment.classificationLabel}
        </span>
      </div>

      {/* Visual Risk Gauge Meter Bar */}
      <div className="bg-slate-50/80 rounded-xl p-3 border border-slate-100 mb-3">
        <div className="flex items-center justify-between text-xs mb-1.5 font-semibold">
          <span className="text-slate-600">Simulated Risk Index:</span>
          <span className="font-black text-slate-900 text-sm">
            {hasScore ? `${score}/100` : 'N/A'}
          </span>
        </div>

        {/* Triple Zone Gradient Bar */}
        <div className="relative w-full h-3 rounded-full bg-slate-200 overflow-hidden flex">
          <div className="w-[35%] bg-emerald-500 h-full" title="Low Risk Zone" />
          <div className="w-[30%] bg-amber-500 h-full" title="Moderate Risk Zone" />
          <div className="w-[35%] bg-rose-500 h-full" title="High Risk Zone" />
        </div>

        {/* Indicator Marker */}
        {hasScore && (
          <div className="relative w-full h-2 mt-0.5">
            <div
              className="absolute -top-1 w-2.5 h-2.5 bg-slate-900 rounded-full border-2 border-white shadow-sm transition-all duration-500 -translate-x-1/2"
              style={{ left: `${Math.max(4, Math.min(96, score))}%` }}
            />
          </div>
        )}

        <div className="flex justify-between text-[9px] font-bold text-slate-400 mt-1 uppercase">
          <span className="text-emerald-700">Low (0-35)</span>
          <span className="text-amber-700">Moderate (35-65)</span>
          <span className="text-rose-700">High (65-100)</span>
        </div>
      </div>

      {/* 3 Evidence Chips */}
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
          <span className="text-[9px] font-bold text-slate-400 uppercase block">Active Alerts</span>
          <span className="font-extrabold text-slate-800">{assessment.activeCorridorAlerts.length} Active</span>
        </div>
        <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
          <span className="text-[9px] font-bold text-slate-400 uppercase block">Weather Factor</span>
          <span className="font-extrabold text-sky-600">{assessment.weatherHazardFactor ?? 'N/A'}/100</span>
        </div>
        <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
          <span className="text-[9px] font-bold text-slate-400 uppercase block">Sim. Slope</span>
          <span className="font-extrabold text-slate-800">{assessment.terrainFactor ?? 'N/A'}/100</span>
        </div>
      </div>
    </div>
  );
};
