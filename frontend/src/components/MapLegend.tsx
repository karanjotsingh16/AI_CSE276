import React, { useState } from 'react';
import { Layers, ChevronDown, ChevronUp } from 'lucide-react';

export const MapLegend: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="absolute bottom-5 right-5 z-[1000] glass-panel rounded-2xl border border-slate-200/90 shadow-xl text-slate-800 text-xs w-60 overflow-hidden select-none">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="px-3 py-2.5 bg-slate-50/90 border-b border-slate-200/80 flex items-center justify-between cursor-pointer hover:bg-slate-100 transition-colors"
      >
        <div className="flex items-center gap-1.5 font-bold text-slate-900 text-[11px]">
          <Layers className="w-3.5 h-3.5 text-blue-600" />
          <span>MAP LEGEND</span>
        </div>
        {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronUp className="w-3.5 h-3.5 text-slate-400" />}
      </div>

      {isOpen && (
        <div className="p-3 space-y-2 text-[11px]">
          {/* Corridors */}
          <div className="space-y-1.5 pb-2 border-b border-slate-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-4 h-1.5 bg-blue-600 rounded-full shadow-xs"></span>
                <span className="font-semibold text-slate-700">Primary Route</span>
              </div>
              <span className="text-[9px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.2 rounded-full">Selected</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-4 h-1.5 bg-amber-500 rounded-full"></span>
                <span className="font-semibold text-slate-700">Alternate Corridor</span>
              </div>
              <span className="text-[9px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.2 rounded-full">Bypass</span>
            </div>
          </div>

          {/* Infrastructure */}
          <div className="space-y-1.5 pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-full bg-rose-500 text-white flex items-center justify-center text-[9px] font-bold shadow-2xs">✚</span>
              <span className="font-medium text-slate-700">Hospital / Trauma</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-full bg-amber-500 text-white flex items-center justify-center text-[8px] font-bold shadow-2xs">▲</span>
              <span className="font-medium text-slate-700">Relief / Evacuation</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[8px] font-bold shadow-2xs">■</span>
              <span className="font-medium text-slate-700">Logistics Depot</span>
            </div>
          </div>

          {/* K-Means Demand Zones */}
          <div className="space-y-1.5 pb-2 border-b border-slate-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded-md bg-violet-600 text-white flex items-center justify-center text-[8px] font-black border border-white shadow-2xs">★</span>
                <span className="font-semibold text-slate-700">Cluster Centre</span>
              </div>
              <span className="text-[9px] font-bold text-violet-700 bg-violet-50 px-1.5 py-0.2 rounded-full">K-Means</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-teal-600 border border-white shadow-2xs"></span>
                <span className="font-medium text-slate-700">Demand Point (40)</span>
              </div>
              <span className="text-[9px] font-bold text-amber-800 bg-amber-50 px-1.5 py-0.2 rounded-full">Synthetic</span>
            </div>
          </div>

          {/* Radar */}
          <div className="flex items-center justify-between text-slate-600">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-sm bg-gradient-to-r from-blue-400 to-indigo-600 opacity-80 shadow-2xs"></span>
              <span className="font-medium">RainViewer Radar</span>
            </div>
            <span className="text-[9px] font-bold text-sky-600 bg-sky-50 px-1.5 py-0.2 rounded-full">Live</span>
          </div>
        </div>
      )}
    </div>
  );
};
