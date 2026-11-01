import React, { useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
  Clock,
  Compass,
  Package,
  Scale,
  Sparkles
} from 'lucide-react';
import {
  LogisticsMission,
  GoodsType,
  PriorityType,
  VehicleType,
  LocationPoint
} from '../../types/mission';
import { RoutePreference } from '../../types/route';
import { PREFERENCE_CONFIGS } from '../../logic/routeScoring';

interface LogisticsMissionCardProps {
  mission: LogisticsMission;
  locations: LocationPoint[];
  preference: RoutePreference;
  onChangePreference: (preference: RoutePreference) => void;
  onUpdateMission: (newMission: LogisticsMission) => void;
  onContinueToResults?: () => void;
  isLoading?: boolean;
}

const GOODS_OPTIONS: GoodsType[] = [
  'Food Supplies',
  'Medical Supplies',
  'Relief Materials',
  'General Cargo'
];

const PRIORITY_OPTIONS: PriorityType[] = [
  'Low',
  'Normal',
  'High',
  'Emergency'
];

const VEHICLE_OPTIONS: { type: VehicleType; label: string; icon: string }[] = [
  { type: '4×4', label: '4×4 High-Clearance', icon: '🚙' },
  { type: 'Van', label: 'Utility Van (2.5T)', icon: '🚐' },
  { type: 'Small Truck', label: 'Small Truck (6W)', icon: '🚚' },
  { type: 'Heavy Truck', label: 'Heavy Truck (10W)', icon: '🚛' }
];

const PREFERENCE_ORDER: RoutePreference[] = ['balanced', 'shortest', 'fastest'];

export const LogisticsMissionCard: React.FC<LogisticsMissionCardProps> = ({
  mission,
  locations,
  preference,
  onChangePreference,
  onUpdateMission,
  onContinueToResults,
  isLoading = false
}) => {
  const [goods, setGoods] = useState<GoodsType>(mission.goods);
  const [priority, setPriority] = useState<PriorityType>(mission.priority);
  const [quantityKg, setQuantityKg] = useState<number>(mission.quantityKg);
  const [vehicle, setVehicle] = useState<VehicleType>(mission.vehicle);
  const [originId, setOriginId] = useState<string>(mission.originId);
  const [destinationId, setDestinationId] = useState<string>(mission.destinationId);
  const [showCargoDetails, setShowCargoDetails] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const applyMissionChange = (
    nextOriginId: string,
    nextDestinationId: string,
    nextGoods: GoodsType = goods,
    nextPriority: PriorityType = priority,
    nextQuantityKg: number = quantityKg,
    nextVehicle: VehicleType = vehicle
  ): boolean => {
    if (!nextQuantityKg || isNaN(nextQuantityKg) || nextQuantityKg <= 0) {
      setValidationError('Please enter a positive cargo payload (> 0 kg).');
      return false;
    }
    if (nextOriginId === nextDestinationId) {
      setValidationError('Origin and destination hubs must be different.');
      return false;
    }

    setValidationError(null);
    onUpdateMission({
      goods: nextGoods,
      priority: nextPriority,
      quantityKg: nextQuantityKg,
      vehicle: nextVehicle,
      originId: nextOriginId,
      destinationId: nextDestinationId
    });
    return true;
  };

  const handleOriginChange = (nextOriginId: string) => {
    setOriginId(nextOriginId);
    applyMissionChange(nextOriginId, destinationId);
  };

  const handleDestinationChange = (nextDestinationId: string) => {
    setDestinationId(nextDestinationId);
    applyMissionChange(originId, nextDestinationId);
  };

  const handleSwap = () => {
    const nextOriginId = destinationId;
    const nextDestinationId = originId;
    setOriginId(nextOriginId);
    setDestinationId(nextDestinationId);
    applyMissionChange(nextOriginId, nextDestinationId);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const valid = applyMissionChange(originId, destinationId);
    if (valid && onContinueToResults) {
      onContinueToResults();
    }
  };

  return (
    <div className="animate-step-enter space-y-4">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* SECTION 1: JOURNEY ENDPOINTS */}
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4 card-shadow space-y-3.5">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] font-extrabold uppercase tracking-widest text-blue-600 block">
                Step 1 of 4
              </span>
              <h2 className="text-sm font-extrabold text-slate-900 mt-0.5">
                Where are you dispatching?
              </h2>
            </div>
            <span className="text-[10px] font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
              3,000 m Snap Limit
            </span>
          </div>

          {/* Connected Origin -> Destination Selector */}
          <div className="relative bg-slate-50/90 rounded-2xl p-3.5 border border-slate-200/80 space-y-3">
            {/* Origin */}
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-emerald-500/15 shrink-0" />
              <div className="flex-1 min-w-0">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">
                  Origin Dispatch Hub
                </label>
                <select
                  value={originId}
                  onChange={(e) => handleOriginChange(e.target.value)}
                  className="w-full text-xs font-bold bg-white border border-slate-200/90 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900 transition-all cursor-pointer shadow-2xs"
                >
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.name} ({loc.elevationMeters}m)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Divider + Swap Button */}
            <div className="flex items-center gap-2 pl-1">
              <div className="h-4 border-l-2 border-dashed border-slate-300 ml-0.5" />
              <div className="flex-1 border-t border-slate-200/80" />
              <button
                type="button"
                onClick={handleSwap}
                title="Swap Origin & Destination"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white border border-slate-200 hover:border-blue-400 text-[10px] font-bold text-slate-600 hover:text-blue-600 shadow-2xs transition-all hover:scale-105 active:scale-95 cursor-pointer"
              >
                <ArrowUpDown className="w-3 h-3" />
                <span>Swap</span>
              </button>
            </div>

            {/* Destination */}
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-rose-500 ring-4 ring-rose-500/15 shrink-0" />
              <div className="flex-1 min-w-0">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">
                  Delivery Destination
                </label>
                <select
                  value={destinationId}
                  onChange={(e) => handleDestinationChange(e.target.value)}
                  className="w-full text-xs font-bold bg-white border border-slate-200/90 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900 transition-all cursor-pointer shadow-2xs"
                >
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.name} ({loc.elevationMeters}m)
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Collapsible Cargo & Vehicle Settings */}
          <div>
            <button
              type="button"
              onClick={() => setShowCargoDetails(!showCargoDetails)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100/80 border border-slate-200/70 text-[11px] text-slate-600 font-semibold transition-all cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <Package className="w-3.5 h-3.5 text-blue-600" />
                <span>
                  Payload: <strong className="text-slate-900">{goods}</strong> · {quantityKg} kg ·{' '}
                  <span className="text-blue-700 font-bold">{priority}</span> · {vehicle}
                </span>
              </span>
              {showCargoDetails ? (
                <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              )}
            </button>

            {showCargoDetails && (
              <div className="mt-2 p-3 rounded-xl bg-slate-50/70 border border-slate-200/80 space-y-2.5 animate-fade-in">
                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">
                      Cargo Type
                    </label>
                    <select
                      value={goods}
                      onChange={(e) => {
                        const val = e.target.value as GoodsType;
                        setGoods(val);
                        applyMissionChange(originId, destinationId, val, priority, quantityKg, vehicle);
                      }}
                      className="w-full text-xs font-semibold bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 cursor-pointer"
                    >
                      {GOODS_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">
                      Quantity (kg)
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="50000"
                      value={quantityKg || ''}
                      onChange={(e) => setQuantityKg(Number(e.target.value))}
                      className="w-full text-xs font-semibold bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">
                      Mission Priority
                    </label>
                    <select
                      value={priority}
                      onChange={(e) => {
                        const val = e.target.value as PriorityType;
                        setPriority(val);
                        applyMissionChange(originId, destinationId, goods, val, quantityKg, vehicle);
                      }}
                      className="w-full text-xs font-bold bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 cursor-pointer"
                    >
                      {PRIORITY_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">
                      Vehicle Type
                    </label>
                    <select
                      value={vehicle}
                      onChange={(e) => {
                        const val = e.target.value as VehicleType;
                        setVehicle(val);
                        applyMissionChange(originId, destinationId, goods, priority, quantityKg, val);
                      }}
                      className="w-full text-xs font-semibold bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 cursor-pointer"
                    >
                      {VEHICLE_OPTIONS.map((v) => (
                        <option key={v.type} value={v.type}>
                          {v.icon} {v.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* SECTION 2: ROUTE PREFERENCE */}
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4 card-shadow space-y-3">
          <div>
            <span className="text-[10px] font-extrabold uppercase tracking-widest text-indigo-600 block">
              Optimization Mode
            </span>
            <h2 className="text-sm font-extrabold text-slate-900 mt-0.5">
              How should we rank routes?
            </h2>
          </div>

          <div className="space-y-2">
            {PREFERENCE_ORDER.map((prefKey) => {
              const cfg = PREFERENCE_CONFIGS[prefKey];
              const isSelected = preference === prefKey;

              return (
                <button
                  key={prefKey}
                  type="button"
                  onClick={() => onChangePreference(prefKey)}
                  className={`w-full p-3 rounded-xl border-2 text-left transition-all duration-200 cursor-pointer flex items-center justify-between gap-3 ${
                    isSelected
                      ? 'bg-blue-50/70 border-blue-600 shadow-xs scale-[1.01]'
                      : 'bg-slate-50/50 border-slate-200/80 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                        isSelected
                          ? 'bg-blue-600 text-white shadow-sm'
                          : 'bg-white text-slate-500 border border-slate-200'
                      }`}
                    >
                      {prefKey === 'shortest' ? (
                        <Compass className="w-4 h-4" />
                      ) : prefKey === 'fastest' ? (
                        <Clock className="w-4 h-4" />
                      ) : (
                        <Scale className="w-4 h-4" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-extrabold text-slate-900">
                        {cfg.label}
                      </div>
                      <div className="text-[11px] text-slate-500 truncate mt-0.5">
                        {cfg.description}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-1 rounded-lg shrink-0 ${
                      isSelected
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-slate-600 border border-slate-200'
                    }`}
                  >
                    {Math.round(cfg.distanceWeight * 100)}D / {Math.round(cfg.timeWeight * 100)}T
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Validation Error */}
        {validationError && (
          <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-center gap-2 animate-fade-in">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{validationError}</span>
          </div>
        )}

        {/* PRIMARY CONTINUE / CALCULATE CTA */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-3.5 px-5 rounded-2xl font-extrabold text-xs text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-blue-600/20 hover:shadow-xl hover:scale-[1.01] active:scale-[0.99] transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer"
        >
          {isLoading ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Calculating Optimal Route...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-blue-200" />
              <span>Find Best Route</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>
    </div>
  );
};
