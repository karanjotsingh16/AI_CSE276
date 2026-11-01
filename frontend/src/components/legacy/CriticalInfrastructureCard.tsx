import React from 'react';
import { CriticalFacility, InfraCategory } from '../../types/infrastructure';
import { LocateFixed } from 'lucide-react';

interface CriticalInfrastructureCardProps {
  facilities: CriticalFacility[];
  activeCategories: InfraCategory[];
  onToggleCategory: (cat: InfraCategory) => void;
  onFocusFacility?: (lat: number, lng: number) => void;
}

export const CriticalInfrastructureCard: React.FC<CriticalInfrastructureCardProps> = ({
  facilities,
  activeCategories,
  onToggleCategory,
  onFocusFacility
}) => {
  const categoriesConfig: {
    id: InfraCategory;
    label: string;
    icon: string;
    activeClass: string;
  }[] = [
    {
      id: 'hospital',
      label: 'Hospitals',
      icon: '🏥',
      activeClass: 'bg-rose-500 text-white border-rose-500 shadow-rose-500/20 shadow-sm'
    },
    {
      id: 'relief',
      label: 'Relief Hubs',
      icon: '⛺',
      activeClass: 'bg-amber-500 text-white border-amber-500 shadow-amber-500/20 shadow-sm'
    },
    {
      id: 'logistics',
      label: 'Depots',
      icon: '🏢',
      activeClass: 'bg-blue-600 text-white border-blue-600 shadow-blue-500/20 shadow-sm'
    }
  ];

  const visibleFacilities = facilities.filter(f => activeCategories.includes(f.category));

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-300 p-4 text-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-base shadow-2xs">
            🏥
          </div>
          <div>
            <h2 className="text-[14px] font-bold text-slate-900 leading-none">Critical Infrastructure</h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Mapped Regional Network</p>
          </div>
        </div>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
          {visibleFacilities.length} Points
        </span>
      </div>

      {/* Modern Filter Chips */}
      <div className="flex items-center gap-1.5 mb-3">
        {categoriesConfig.map(cat => {
          const isActive = activeCategories.includes(cat.id);
          const count = facilities.filter(f => f.category === cat.id).length;

          return (
            <button
              key={cat.id}
              onClick={() => onToggleCategory(cat.id)}
              className={`flex-1 flex items-center justify-center gap-1 py-1.5 px-2 rounded-xl text-xs font-bold border transition-all duration-200 cursor-pointer ${
                isActive
                  ? cat.activeClass
                  : 'bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100'
              }`}
            >
              <span>{cat.icon}</span>
              <span>{cat.label}</span>
              <span className={`text-[9px] px-1.5 py-0.2 rounded-full ${isActive ? 'bg-white/20' : 'bg-slate-200 text-slate-600'}`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Facilities Quick-List */}
      <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
        {visibleFacilities.map(facility => (
          <div
            key={facility.id}
            onClick={() => onFocusFacility && onFocusFacility(facility.lat, facility.lng)}
            className="p-2 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-blue-50/50 hover:border-blue-300 transition-all text-left text-xs cursor-pointer flex items-center justify-between group"
          >
            <div className="pr-2">
              <h4 className="font-bold text-slate-900 group-hover:text-blue-600 transition-colors leading-tight text-[11px]">
                {facility.name}
              </h4>
              <p className="text-[10px] text-slate-400 truncate mt-0.5">{facility.capacityOrType}</p>
            </div>
            <button
              type="button"
              className="p-1 rounded-lg bg-white border border-slate-200 text-slate-400 group-hover:text-blue-600 group-hover:border-blue-300 shrink-0 shadow-2xs transition-colors"
              title="Locate on map"
            >
              <LocateFixed className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
