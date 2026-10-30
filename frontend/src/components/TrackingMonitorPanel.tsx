import React, { useState, useEffect, useCallback } from 'react';
import {
  Truck,
  AlertTriangle,
  Play,
  CheckCircle2,
  Clock,
  MapPin,
  RefreshCw,
  Eye,
  PlusCircle,
  Gauge,
  Compass,
} from 'lucide-react';
import { Vehicle, Delivery } from '../types/tracking';
import {
  fetchVehicles,
  fetchDeliveries,
  stepSimulatedDelivery,
} from '../services/trackingService';

interface TrackingMonitorPanelProps {
  onSelectVehicle?: (vehicle: Vehicle) => void;
  onSelectDelivery?: (delivery: Delivery) => void;
  onRequestNewDelivery?: () => void;
}

export const TrackingMonitorPanel: React.FC<TrackingMonitorPanelProps> = ({
  onSelectVehicle,
  onSelectDelivery: _onSelectDelivery,
  onRequestNewDelivery,
}) => {
  const [activeTab, setActiveTab] = useState<'deliveries' | 'fleet'>('deliveries');
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSteppingId, setIsSteppingId] = useState<string | null>(null);
  const [simulateDeviationMap, setSimulateDeviationMap] = useState<Record<string, boolean>>({});

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [vList, dList] = await Promise.all([
        fetchVehicles(),
        fetchDeliveries(),
      ]);
      setVehicles(vList);
      setDeliveries(dList);
    } catch (err) {
      console.error('Error loading tracking data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStepSimulation = async (deliveryId: string) => {
    setIsSteppingId(deliveryId);
    const shouldDeviate = Boolean(simulateDeviationMap[deliveryId]);
    try {
      await stepSimulatedDelivery(deliveryId, 8.0, shouldDeviate);
      await loadData();
    } catch (err) {
      console.error('Simulation step error:', err);
    } finally {
      setIsSteppingId(null);
    }
  };

  const toggleDeviationForDelivery = (deliveryId: string) => {
    setSimulateDeviationMap((prev) => ({
      ...prev,
      [deliveryId]: !prev[deliveryId],
    }));
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'in_transit':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-100 text-sky-800 border border-sky-200 flex items-center gap-1">
            <Truck className="w-2.5 h-2.5" /> IN TRANSIT
          </span>
        );
      case 'delayed':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" /> DELAYED
          </span>
        );
      case 'delivered':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5" /> DELIVERED
          </span>
        );
      case 'interrupted':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            INTERRUPTED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {status.toUpperCase()}
          </span>
        );
    }
  };

  return (
    <div className="space-y-3 text-xs">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex items-center gap-1.5 font-medium text-slate-700">
          <Truck className="w-4 h-4 text-sky-600" />
          <span>GPS Fleet & Delivery Operations (Module F)</span>
        </div>
        {onRequestNewDelivery && (
          <button
            type="button"
            onClick={onRequestNewDelivery}
            className="px-2.5 py-1 rounded-md bg-sky-600 text-white font-medium hover:bg-sky-700 cursor-pointer text-[11px] inline-flex items-center gap-1"
          >
            <PlusCircle className="w-3 h-3" /> Dispatch Cargo
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 p-0.5 rounded-lg bg-slate-100 border border-slate-200 text-[11px]">
          <button
            type="button"
            onClick={() => setActiveTab('deliveries')}
            className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer ${
              activeTab === 'deliveries' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Active Deliveries ({deliveries.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('fleet')}
            className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer ${
              activeTab === 'fleet' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Fleet Vehicles ({vehicles.length})
          </button>
        </div>

        <button
          type="button"
          onClick={loadData}
          className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          title="Refresh Tracking Data"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Tab 1: Deliveries */}
      {activeTab === 'deliveries' && (
        <div className="space-y-2.5 max-h-80 overflow-y-auto pr-0.5">
          {deliveries.length === 0 ? (
            <div className="py-6 text-center text-slate-400">No active delivery missions.</div>
          ) : (
            deliveries.map((del) => {
              const assignedVeh = vehicles.find((v) => v.vehicle_id === del.vehicle_id);
              const isDeviated = del.is_deviated;
              const willDeviate = Boolean(simulateDeviationMap[del.delivery_id]);

              return (
                <div
                  key={del.delivery_id}
                  className={`p-3 rounded-xl bg-white border transition-all space-y-2 ${
                    isDeviated
                      ? 'border-rose-300 shadow-xs ring-1 ring-rose-200'
                      : 'border-slate-200 shadow-2xs hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="font-semibold text-slate-900 leading-snug">{del.title}</h4>
                      <p className="text-[10px] text-slate-500">
                        {del.goods_category} • Priority: <span className="font-medium text-slate-700 uppercase">{del.priority}</span>
                      </p>
                    </div>
                    {getStatusBadge(del.status)}
                  </div>

                  {/* Route Corridor Endpoints */}
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-600 bg-slate-50 rounded-lg p-1.5 border border-slate-100">
                    <MapPin className="w-3 h-3 text-emerald-600 shrink-0" />
                    <span className="truncate">{del.origin_name}</span>
                    <span className="text-slate-400 font-bold">→</span>
                    <MapPin className="w-3 h-3 text-rose-600 shrink-0" />
                    <span className="truncate">{del.destination_name}</span>
                  </div>

                  {/* Progress Bar & ETA */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>Trip Progress: <strong>{del.progress_pct.toFixed(0)}%</strong></span>
                      <span>
                        {del.status === 'delivered'
                          ? 'Arrived'
                          : `ETA: ${del.estimated_arrival_time ? new Date(del.estimated_arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Calculating...'}`}
                      </span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 rounded-full ${
                          del.status === 'delivered'
                            ? 'bg-emerald-500'
                            : isDeviated
                            ? 'bg-rose-500'
                            : 'bg-sky-600'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(5, del.progress_pct))}%` }}
                      />
                    </div>
                  </div>

                  {/* Route Deviation Alert */}
                  {isDeviated && (
                    <div className="p-2 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-[11px] flex items-start gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
                      <div>
                        <strong className="block font-semibold">Route Deviation Detected:</strong>
                        Vehicle is {del.deviation_distance_m.toFixed(0)} m off planned corridor.
                      </div>
                    </div>
                  )}

                  {/* Assigned Vehicle & Telemetry Status */}
                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-100">
                    <span>
                      Vehicle: <strong className="text-slate-800">{del.vehicle_id}</strong> ({assignedVeh?.assigned_driver_name})
                    </span>
                    <div className="flex items-center gap-1.5">
                      {assignedVeh && onSelectVehicle && (
                        <button
                          type="button"
                          onClick={() => onSelectVehicle(assignedVeh)}
                          className="text-sky-600 hover:text-sky-800 font-medium inline-flex items-center gap-0.5 cursor-pointer"
                        >
                          <Eye className="w-3 h-3" /> Focus Map
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Demonstration Simulation Controls */}
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] text-slate-600 font-medium">
                      <span>Simulated GPS Controller (Demo)</span>
                      <button
                        type="button"
                        onClick={() => toggleDeviationForDelivery(del.delivery_id)}
                        className={`px-1.5 py-0.5 rounded text-[9px] font-semibold transition-colors cursor-pointer ${
                          willDeviate
                            ? 'bg-rose-100 text-rose-700 border border-rose-300'
                            : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        {willDeviate ? 'Offset Active (+800m)' : 'Inject Off-Corridor'}
                      </button>
                    </div>

                    <div className="flex items-center justify-between gap-2">
                      <button
                        type="button"
                        disabled={isSteppingId === del.delivery_id || del.status === 'delivered'}
                        onClick={() => handleStepSimulation(del.delivery_id)}
                        className="flex-1 py-1 rounded bg-slate-900 text-white font-medium hover:bg-slate-800 disabled:opacity-50 inline-flex items-center justify-center gap-1 cursor-pointer text-[10px]"
                      >
                        <Play className="w-2.5 h-2.5" />
                        {isSteppingId === del.delivery_id ? 'Advancing GPS...' : 'Step Sim (+8%)'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tab 2: Fleet Vehicles */}
      {activeTab === 'fleet' && (
        <div className="space-y-2 max-h-80 overflow-y-auto pr-0.5">
          {vehicles.map((v) => (
            <div
              key={v.vehicle_id}
              className="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-1.5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-semibold text-slate-900 leading-tight">{v.name}</h4>
                  <p className="text-[10px] text-slate-500">
                    ID: <span className="font-mono font-medium text-slate-700">{v.vehicle_id}</span> • Type: {v.vehicle_type}
                  </p>
                </div>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {v.capacity_kg} kg
                </span>
              </div>

              <div className="grid grid-cols-2 gap-1.5 text-[10px] text-slate-600 bg-slate-50 rounded-lg p-1.5">
                <div className="flex items-center gap-1">
                  <Gauge className="w-3 h-3 text-slate-400" />
                  <span>Speed: <strong>{v.current_speed_kph.toFixed(0)} km/h</strong></span>
                </div>
                <div className="flex items-center gap-1">
                  <Compass className="w-3 h-3 text-slate-400" />
                  <span>Bearing: <strong>{v.current_bearing.toFixed(0)}°</strong></span>
                </div>
                <div className="col-span-2 text-slate-500">
                  Driver: <strong className="text-slate-800">{v.assigned_driver_name}</strong> ({v.assigned_driver_contact || 'No phone'})
                </div>
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
                <span>Source: {v.telemetry_mode}</span>
                {onSelectVehicle && (
                  <button
                    type="button"
                    onClick={() => onSelectVehicle(v)}
                    className="text-sky-600 hover:text-sky-800 font-medium inline-flex items-center gap-1 cursor-pointer"
                  >
                    <Eye className="w-3 h-3" /> Focus Location
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Academic Integrity Notice */}
      <div className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200/70 rounded-lg p-2 leading-relaxed">
        <strong>Academic Integrity Notice:</strong> Real GPS positions are accepted via authenticated telemetry. The simulator uses synthetic step progression along the network polyline to demonstrate route tracking and off-corridor deviation detection.
      </div>
    </div>
  );
};
