import React, { useState } from 'react';
import {
  Route,
  Clock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Navigation,
  Info,
} from 'lucide-react';
import { RouteAlternative } from '../types/route';

interface RouteAlternativesCardProps {
  routes: RouteAlternative[];
  selectedRouteId: string;
  onSelectRoute: (id: string) => void;
  isLoading: boolean;
  defaultExpanded?: boolean;
}

export const RouteAlternativesCard: React.FC<RouteAlternativesCardProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
  isLoading,
  defaultExpanded = false,
}) => {
  const [showAlternatives, setShowAlternatives] = useState<boolean>(defaultExpanded);

  if (isLoading && routes.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-4 animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/2 mb-3"></div>
        <div className="space-y-2">
          <div className="h-16 bg-slate-100 rounded-lg"></div>
          <div className="h-16 bg-slate-100 rounded-lg"></div>
        </div>
      </div>
    );
  }

  if (routes.length === 0) return null;

  const recommended = routes[0];
  const alternatives = routes.slice(1);
  const routesAreIdentical = recommended.evaluation?.routesAreIdentical ?? false;

  const renderRouteCard = (route: RouteAlternative, isPrimary: boolean) => {
    const isSelected = route.id === selectedRouteId;
    const evalData = route.evaluation;
    const rc = evalData?.roadClassBreakdownPct;

    return (
      <div
        key={route.id}
        onClick={() => onSelectRoute(route.id)}
        className={`p-3 rounded-xl border transition-all cursor-pointer ${
          isSelected
            ? 'bg-blue-50/70 border-blue-500 ring-1 ring-blue-500/30 shadow-xs'
            : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/60'
        }`}
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center space-x-2">
            <span
              className="w-3 h-3 rounded-full shrink-0 mt-0.5"
              style={{ backgroundColor: route.color }}
            />
            <div>
              <h4 className="text-xs font-bold text-slate-800 leading-snug">
                {route.name}
              </h4>
              <span className="text-[10px] text-slate-500 font-medium block">
                {route.via}
              </span>
            </div>
          </div>

          <span
            className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded-md border shrink-0 flex items-center gap-1 ${
              isPrimary
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}
          >
            {isPrimary && <CheckCircle2 className="w-2.5 h-2.5" />}
            {route.status}
          </span>
        </div>

        {/* Core Route Metrics */}
        <div className="grid grid-cols-4 gap-1.5 bg-slate-50 p-2 rounded-lg border border-slate-100 mb-2">
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">
              Distance
            </span>
            <span className="text-xs font-extrabold text-slate-800">
              {route.distanceKm} km
            </span>
          </div>

          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">
              Est. Time
            </span>
            <span className="text-xs font-extrabold text-slate-800 flex items-center gap-0.5">
              <Clock className="w-3 h-3 text-slate-400" />
              {route.durationMinutes} m
            </span>
          </div>

          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">
              Arterial
            </span>
            <span className="text-xs font-extrabold text-indigo-700">
              {rc ? `${rc.major_arterial}%` : 'N/A'}
            </span>
          </div>

          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">
              Score
            </span>
            <span className="text-xs font-black text-blue-700">
              {evalData?.weightedScore ?? route.logisticsScore}
              <span className="text-[9px] font-semibold text-slate-400">/100</span>
            </span>
          </div>
        </div>

        {/* Component Score Pills */}
        {evalData && (
          <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
            <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-100">
              S_dist: {evalData.distanceScore}
            </span>
            <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold border border-emerald-100">
              S_time: {evalData.timeScore}
            </span>
            <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-semibold border border-indigo-100">
              S_hierarchy: {evalData.roadHierarchyScore}
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
              Avg: {evalData.impliedAvgSpeedKmh} km/h
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 overflow-hidden">
      <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Route className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Route Candidates on Map
          </h3>
        </div>
        <span className="text-[10px] font-semibold text-slate-500">
          Click card to highlight on map
        </span>
      </div>

      <div className="p-3.5 space-y-2.5">
        {renderRouteCard(recommended, true)}

        {routesAreIdentical && alternatives.length > 0 && (
          <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-2 text-[11px] text-slate-600">
            <Info className="w-3.5 h-3.5 text-blue-500 shrink-0" />
            <span>
              Shortest-distance and fastest-estimated searches converged on the exact same road path for this corridor.
            </span>
          </div>
        )}

        {alternatives.length > 0 && (
          <div>
            <button
              type="button"
              onClick={() => setShowAlternatives((prev) => !prev)}
              className="w-full py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-bold text-slate-700 flex items-center justify-between transition-colors cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <Navigation className="w-3.5 h-3.5 text-amber-600" />
                {showAlternatives
                  ? 'Hide Alternative Route'
                  : `Show Alternative Route (${alternatives[0].distanceKm} km · ${alternatives[0].durationMinutes} min est.)`}
              </span>
              {showAlternatives ? (
                <ChevronUp className="w-4 h-4 text-slate-500" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-500" />
              )}
            </button>

            {showAlternatives && (
              <div className="mt-2.5 space-y-2">
                {alternatives.map((alt) => renderRouteCard(alt, false))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
