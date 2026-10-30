import React, { useState } from 'react';
import { X, Truck, ShieldAlert, Loader2 } from 'lucide-react';
import { Vehicle, GoodsCategory, DeliveryPriority, Delivery } from '../types/tracking';
import { createDelivery } from '../services/trackingService';
import { RouteAlternative } from '../types/route';

interface NewDeliveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  vehicles: Vehicle[];
  activeRoute?: RouteAlternative;
  originName?: string;
  destinationName?: string;
  onDeliveryCreated?: (delivery: Delivery) => void;
}

export const NewDeliveryModal: React.FC<NewDeliveryModalProps> = ({
  isOpen,
  onClose,
  vehicles,
  activeRoute,
  originName = 'Shillong Central Hub',
  destinationName = 'Sohra CHC',
  onDeliveryCreated,
}) => {
  const [selectedVehicleId, setSelectedVehicleId] = useState<string>(
    vehicles[0]?.vehicle_id || 'ML-05-TR-1042'
  );
  const [title, setTitle] = useState<string>('Essential Medical Supply Dispatch');
  const [goodsCategory, setGoodsCategory] = useState<GoodsCategory>('Medical Supplies');
  const [priority, setPriority] = useState<DeliveryPriority>('High');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeRoute || activeRoute.coordinates.length < 2) {
      setErrorMsg('No active route geometry available. Calculate a route first.');
      return;
    }
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      const originPt = activeRoute.coordinates[0];
      const destPt = activeRoute.coordinates[activeRoute.coordinates.length - 1];

      const delivery = await createDelivery({
        vehicle_id: selectedVehicleId,
        title: title.trim(),
        goods_category: goodsCategory,
        priority,
        origin_name: originName,
        origin_lat: originPt[0],
        origin_lng: originPt[1],
        destination_name: destinationName,
        destination_lat: destPt[0],
        destination_lng: destPt[1],
        planned_distance_km: activeRoute.distanceKm,
        planned_duration_minutes: activeRoute.durationMinutes,
        planned_route_geometry: activeRoute.coordinates,
        dispatch_immediately: true,
      });

      if (onDeliveryCreated) {
        onDeliveryCreated(delivery);
      }
      onClose();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to create delivery mission');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-400">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold tracking-wide">
                Dispatch Cargo Delivery Mission
              </h2>
              <p className="text-[11px] text-slate-300">
                Assign Fleet Vehicle & Begin GPS Tracking (Module F)
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Active Route Summary Pill */}
          {activeRoute && (
            <div className="p-3 rounded-xl bg-sky-50 border border-sky-200/80 space-y-1">
              <div className="text-[10px] font-bold text-sky-900 uppercase">
                Active Calculated Corridor
              </div>
              <div className="text-xs font-semibold text-slate-800">
                {originName} → {destinationName}
              </div>
              <div className="flex items-center gap-4 text-[11px] text-sky-800 pt-0.5">
                <span>Distance: <strong>{activeRoute.distanceKm} km</strong></span>
                <span>Est. Duration: <strong>{activeRoute.durationMinutes.toFixed(0)} min</strong></span>
                <span>Waypoints: <strong>{activeRoute.coordinates.length} pts</strong></span>
              </div>
            </div>
          )}

          {/* Title */}
          <div className="space-y-1">
            <label className="font-medium text-slate-700">Mission Title *</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-800"
            />
          </div>

          {/* Vehicle Assignment & Goods Category */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="font-medium text-slate-700">Assign Vehicle *</label>
              <select
                value={selectedVehicleId}
                onChange={(e) => setSelectedVehicleId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white"
              >
                {vehicles.map((v) => (
                  <option key={v.vehicle_id} value={v.vehicle_id}>
                    {v.vehicle_id} ({v.name} - {v.vehicle_type})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="font-medium text-slate-700">Goods Category *</label>
              <select
                value={goodsCategory}
                onChange={(e) => setGoodsCategory(e.target.value as GoodsCategory)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white"
              >
                <option value="Medical Supplies">Medical Supplies</option>
                <option value="Food Supplies">Food Supplies</option>
                <option value="Relief Materials">Relief Materials</option>
                <option value="Vaccines / Cold Chain">Vaccines / Cold Chain</option>
                <option value="General Cargo">General Cargo</option>
              </select>
            </div>
          </div>

          {/* Priority */}
          <div className="space-y-1">
            <label className="font-medium text-slate-700">Priority Tier *</label>
            <div className="grid grid-cols-4 gap-1.5">
              {(['Emergency', 'High', 'Normal', 'Low'] as DeliveryPriority[]).map((pri) => (
                <button
                  key={pri}
                  type="button"
                  onClick={() => setPriority(pri)}
                  className={`py-1.5 rounded-lg text-center font-medium border transition-all cursor-pointer ${
                    priority === pri
                      ? pri === 'Emergency'
                        ? 'bg-rose-600 text-white border-rose-600'
                        : pri === 'High'
                        ? 'bg-sky-600 text-white border-sky-600'
                        : 'bg-slate-900 text-white border-slate-900'
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {pri}
                </button>
              ))}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-slate-600 hover:bg-slate-100 font-medium transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-sky-600 text-white font-medium hover:bg-sky-700 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Dispatching...
                </>
              ) : (
                'Confirm Dispatch & Track'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
