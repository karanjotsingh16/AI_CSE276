import React from 'react';
import {
  DemandZonesResponse,
  DemandZoneErrorState,
  getClusterColor
} from '../types/demandZone';
import {
  Network,
  AlertTriangle,
  RefreshCw,
  Eye,
  EyeOff,
  MapPin,
  Info,
  SlidersHorizontal
} from 'lucide-react';

interface DemandZonesCardProps {
  data: DemandZonesResponse | null;
  isLoading: boolean;
  error: DemandZoneErrorState | null;
  nClusters: number;
  showOnMap: boolean;
  onChangeClusterCount: (k: number) => void;
  onToggleShowOnMap: () => void;
  onRetry: () => void;
  onFocusClusterCenter: (lat: number, lng: number) => void;
}

const CLUSTER_COUNT_OPTIONS = [2, 3, 4, 5, 6];

export const DemandZonesCard: React.FC<DemandZonesCardProps> = ({
  data,
  isLoading,
  error,
  nClusters,
  showOnMap,
  onChangeClusterCount,
  onToggleShowOnMap,
  onRetry,
  onFocusClusterCenter
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 p-4 card-shadow">
      {/* Header */}
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-violet-50 border border-violet-200/60 flex items-center justify-center text-violet-600">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-800">
              K-Means Demand Zones
            </h2>
            <p className="text-[11px] text-slate-500">
              Unsupervised spatial demand clustering (UTM 46N)
            </p>
          </div>
        </div>

        <button
          onClick={onToggleShowOnMap}
          title={showOnMap ? 'Hide demand zones on map' : 'Show demand zones on map'}
          className={`flex items-center gap-1 text-[10px] font-bold px-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
            showOnMap
              ? 'bg-violet-50 text-violet-700 border-violet-200 hover:bg-violet-100'
              : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
          }`}
        >
          {showOnMap ? (
            <>
              <Eye className="w-3 h-3" />
              <span>Map Overlay On</span>
            </>
          ) : (
            <>
              <EyeOff className="w-3 h-3" />
              <span>Map Overlay Off</span>
            </>
          )}
        </button>
      </div>

      {/* Required Synthetic Provenance Banner */}
      <div className="mb-3 px-2.5 py-2 rounded-xl bg-amber-50/95 border border-amber-300/90 text-[10px] text-amber-950 font-extrabold tracking-tight flex items-start gap-1.5">
        <Info className="w-3.5 h-3.5 text-amber-700 shrink-0 mt-0.5" />
        <div>
          <div>DEMONSTRATION DATA — SYNTHETIC DEMAND, NOT REAL-WORLD OBSERVATIONS.</div>
          {data?.data_provenance?.provenance_note && (
            <div className="font-normal text-amber-800 mt-0.5 leading-snug">
              Source tag: <span className="font-mono font-semibold">{data.data_provenance.data_sources.join(', ')}</span> ({data.dataset_size} points, {data.total_demand_units} total units)
            </div>
          )}
        </div>
      </div>

      {/* Configuration Bar (n_clusters & random_state) */}
      <div className="mb-3 p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
          <SlidersHorizontal className="w-3.5 h-3.5 text-violet-600" />
          <span>Config:</span>
          <span className="font-mono text-[10px] bg-white px-1.5 py-0.5 rounded border border-slate-200">
            n_clusters={data?.n_clusters ?? nClusters}
          </span>
          <span className="font-mono text-[10px] bg-white px-1.5 py-0.5 rounded border border-slate-200">
            random_state={data?.random_state ?? 42}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-[10px] text-slate-500 font-semibold mr-0.5">K:</span>
          {CLUSTER_COUNT_OPTIONS.map((k) => {
            const active = nClusters === k;
            return (
              <button
                key={k}
                disabled={isLoading}
                onClick={() => onChangeClusterCount(k)}
                className={`w-5 h-5 rounded text-[10px] font-extrabold transition-colors cursor-pointer ${
                  active
                    ? 'bg-violet-600 text-white shadow-2xs'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {k}
              </button>
            );
          })}
        </div>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div className="space-y-2 py-2">
          <div className="h-14 rounded-xl bg-slate-100 animate-pulse" />
          <div className="h-16 rounded-xl bg-slate-100 animate-pulse" />
          <div className="text-center text-[11px] text-slate-500 font-medium">
            Fitting K-Means on projected UTM Zone 46N coordinates via FastAPI...
          </div>
        </div>
      ) : error ? (
        /* Error + Retry State */
        <div className="p-3.5 rounded-xl border bg-rose-50/90 border-rose-200 text-rose-950">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-extrabold tracking-tight">{error.title}</div>
              <p className="text-[11px] mt-1 leading-relaxed text-rose-800">{error.detail}</p>
              <div className="mt-2.5 flex items-center gap-2">
                <button
                  onClick={onRetry}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white border border-slate-300 text-slate-800 hover:bg-slate-50 shadow-2xs cursor-pointer"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Retry Clustering</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : data ? (
        <>
          {/* Internal Evaluation Metrics Box */}
          <div className="mb-3 p-2.5 rounded-xl bg-violet-50/50 border border-violet-200/70">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-violet-900">
                Internal Clustering Evaluation Metrics
              </span>
              <span className="text-[9px] font-mono font-semibold text-violet-700 bg-violet-100/80 px-1.5 py-0.5 rounded">
                {data.coordinate_projection.clustering_crs} ({data.coordinate_projection.clustering_units})
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-center my-1.5">
              <div className="bg-white p-2 rounded-lg border border-violet-100">
                <div className="text-[10px] text-slate-500 font-semibold">Silhouette Score</div>
                <div className="text-sm font-black text-slate-900 font-mono mt-0.5">
                  {data.evaluation_metrics.silhouette_score !== null
                    ? data.evaluation_metrics.silhouette_score.toFixed(4)
                    : 'N/A'}
                </div>
                <div className="text-[9px] text-slate-400">Range [-1, 1] · Higher = denser</div>
              </div>

              <div className="bg-white p-2 rounded-lg border border-violet-100">
                <div className="text-[10px] text-slate-500 font-semibold">Davies–Bouldin Index</div>
                <div className="text-sm font-black text-slate-900 font-mono mt-0.5">
                  {data.evaluation_metrics.davies_bouldin_score !== null
                    ? data.evaluation_metrics.davies_bouldin_score.toFixed(4)
                    : 'N/A'}
                </div>
                <div className="text-[9px] text-slate-400">≥ 0 · Lower = better separation</div>
              </div>
            </div>

            <p className="text-[10px] text-slate-600 leading-snug mt-1">
              <strong>Note:</strong> Silhouette and Davies–Bouldin scores are{' '}
              <span className="underline decoration-violet-400">internal unsupervised clustering metrics</span>{' '}
              measuring geometric cohesion and separation in projected metres —{' '}
              <strong>not predictive or supervised accuracy</strong>.
            </p>
          </div>

          {/* Cluster Summary Table / List */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1">
              <span>Cluster Zone & Centre</span>
              <span>Points · Total Demand</span>
            </div>

            {data.clusters.map((cluster) => {
              const color = getClusterColor(cluster.cluster_id);
              return (
                <div
                  key={cluster.cluster_id}
                  onClick={() => onFocusClusterCenter(cluster.center_lat, cluster.center_lng)}
                  title="Click to focus map on this cluster centre"
                  className="p-2.5 rounded-xl border border-slate-200/90 bg-slate-50/70 hover:bg-slate-100/80 transition-all cursor-pointer flex items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span
                      className="w-3.5 h-3.5 rounded-md shrink-0 shadow-2xs border border-white"
                      style={{ backgroundColor: color }}
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-extrabold text-slate-900">
                          Zone #{cluster.cluster_id}
                        </span>
                        <span className="text-[10px] font-semibold text-slate-500 bg-white px-1.5 py-0.2 rounded border border-slate-200">
                          {cluster.demand_share_pct.toFixed(1)}% share
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono flex items-center gap-1 mt-0.5">
                        <MapPin className="w-2.5 h-2.5 text-slate-400 shrink-0" />
                        <span>
                          {cluster.center_lat.toFixed(4)}°N, {cluster.center_lng.toFixed(4)}°E
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-xs font-black text-slate-900">
                      {cluster.total_demand_units.toFixed(0)} <span className="text-[10px] font-bold text-slate-500">units</span>
                    </div>
                    <div className="text-[10px] font-semibold text-slate-600">
                      {cluster.point_count} {cluster.point_count === 1 ? 'point' : 'points'} · mean {cluster.mean_distance_to_center_m.toFixed(0)}m
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : null}
    </div>
  );
};

