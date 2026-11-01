import { useState, useEffect, useCallback } from 'react';
import { MapView } from './components/map/MapView';
import { LocationSearchInput } from './components/common/LocationSearchInput';

import {
  NER_LOCATIONS,
  DEFAULT_ORIGIN_ID,
  DEFAULT_DESTINATION_ID,
} from './data/locations';
import {
  LogisticsMission,
  GoodsType,
  PriorityType,
  VehicleType,
} from './types/mission';
import { CriticalFacility, InfraCategory } from './types/infrastructure';
import {
  RouteAlternative,
  RouteErrorState,
  RoutePreference,
} from './types/route';
import { DisasterAlert } from './types/alert';
import { RadarState } from './types/radar';
import {
  DemandZonesResponse,
  DemandZoneErrorState,
  getClusterColor,
} from './types/demandZone';
import { GeocodedLocationResult } from './types/geocoding';
import { RoadSegment, IncidentReport } from './types/accessibility';
import {
  fetchRoadSegments,
  fetchIncidents,
} from './services/accessibilityService';
import { FieldReportModal } from './components/modals/FieldReportModal';
import { AccessibilityMonitorPanel } from './components/panels/AccessibilityMonitorPanel';
import { Vehicle, Delivery } from './types/tracking';
import {
  fetchVehicles,
  fetchDeliveries,
} from './services/trackingService';
import { TrackingMonitorPanel } from './components/panels/TrackingMonitorPanel';
import { NewDeliveryModal } from './components/modals/NewDeliveryModal';
import { fetchUnreadCount } from './services/notificationService';
import { NotificationCenterModal } from './components/modals/NotificationCenterModal';
import { useTranslation } from './i18n';
import { subscribeToOfflineQueue } from './services/offlineQueueService';
import { OfflineQueueModal } from './components/modals/OfflineQueueModal';

import {
  calculateRouteAlternatives,
  RouteApiError,
} from './services/routeService';
import {
  evaluateAndRankRoutes,
  PREFERENCE_CONFIGS,
} from './logic/routeScoring';
import { formatDurationHoursMinutes } from './logic/formatters';
import {
  fetchDemandZones,
  DemandZoneApiError,
} from './services/demandZoneService';
import {
  convertGeocodedToLocationPoint,
  fetchDefaultLocationSuggestions,
} from './services/geocodingService';
import { fetchGovernmentDisasterAlerts } from './services/alertService';

import {
  ArrowRight,
  ArrowLeft,
  ArrowUpDown,
  Loader2,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  AlertCircle,
  ShieldAlert,
  Truck,
  Bell,
  Wifi,
  WifiOff,
  Globe,
} from 'lucide-react';

type AppStage = 'welcome' | 'endpoints' | 'details' | 'calculating' | 'workspace';

const GOODS_OPTIONS: GoodsType[] = [
  'Medical Supplies',
  'Food Supplies',
  'Relief Materials',
  'General Cargo',
];

const PRIORITY_OPTIONS: PriorityType[] = ['Emergency', 'High', 'Normal', 'Low'];

const VEHICLE_OPTIONS: VehicleType[] = [
  '4×4',
  'Van',
  'Small Truck',
  'Heavy Truck',
];

const DEFAULT_ACTIVE_INFRA: InfraCategory[] = [];
const DEFAULT_FACILITIES: CriticalFacility[] = [];

const INITIAL_RADAR: RadarState = {
  isActive: false,
  isPlaying: false,
  frames: [],
  currentFrameIndex: 0,
  lastUpdated: null,
  isLoading: false,
  error: null,
  host: 'https://tilecache.rainviewer.com',
};

function buildInitialGeocodedLocation(locId: string): GeocodedLocationResult {
  const found = NER_LOCATIONS.find((l) => l.id === locId) || NER_LOCATIONS[0];
  return {
    place_id: found.id,
    name: found.name,
    display_name: `${found.name}, ${found.state}, India`,
    state: found.state,
    lat: found.lat,
    lng: found.lng,
    elevation_m: found.elevationMeters,
    place_type: found.type,
    source: 'verified_local_gazetteer',
    description: found.description,
    coverage: {
      within_loaded_graph: true,
      status: 'routable_in_loaded_graph',
      region_id: 'meghalaya_shillong_sohra',
      region_name: 'East & West Khasi Hills (Shillong–Sohra)',
      nearest_node_id: found.id === 'shillong' ? 3428125750 : 9667317115,
      nearest_node_lat: found.lat,
      nearest_node_lng: found.lng,
      snap_distance_m: found.id === 'shillong' ? 5.84 : 18.25,
      max_snap_distance_m: 3000.0,
      matching_catalog_regions: ['meghalaya_shillong_sohra'],
      acquire_command: null,
      message: 'Within loaded Shillong–Sohra road network coverage.',
    },
  };
}

export function App() {
  const [appStage, setAppStage] = useState<AppStage>('welcome');
  const [focusTarget, setFocusTarget] = useState<[number, number] | null>(null);

  // Progressive disclosure toggles in the workspace panel (collapsed by default)
  const [showScoreDetails, setShowScoreDetails] = useState<boolean>(false);
  const [showDemandSection, setShowDemandSection] = useState<boolean>(false);
  const [showMlSection, setShowMlSection] = useState<boolean>(false);
  const [showAccessibilitySection, setShowAccessibilitySection] = useState<boolean>(false);
  const [showTrackingSection, setShowTrackingSection] = useState<boolean>(false);

  // Road Accessibility & Field Reports (Module D & E)
  const [roadSegments, setRoadSegments] = useState<RoadSegment[]>([]);
  const [fieldIncidents, setFieldIncidents] = useState<IncidentReport[]>([]);
  const [isFieldReportModalOpen, setIsFieldReportModalOpen] = useState<boolean>(false);

  // GPS Vehicle & Delivery Tracking (Module F)
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [isNewDeliveryModalOpen, setIsNewDeliveryModalOpen] = useState<boolean>(false);

  // Alerts & Notifications (Module G)
  const [unreadAlertCount, setUnreadAlertCount] = useState<number>(0);
  const [isNotificationModalOpen, setIsNotificationModalOpen] = useState<boolean>(false);

  // Multilingual & Offline PWA Sync Queue (Module H / Phase 7)
  const { t, language, setLanguage } = useTranslation();
  const [isOfflineQueueOpen, setIsOfflineQueueOpen] = useState<boolean>(false);
  const [offlineDraftsCount, setOfflineDraftsCount] = useState<number>(0);
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  // Origin & Destination
  const [originGeo, setOriginGeo] = useState<GeocodedLocationResult>(() =>
    buildInitialGeocodedLocation(DEFAULT_ORIGIN_ID)
  );
  const [destinationGeo, setDestinationGeo] = useState<GeocodedLocationResult>(
    () => buildInitialGeocodedLocation(DEFAULT_DESTINATION_ID)
  );
  const [locationSuggestions, setLocationSuggestions] = useState<
    GeocodedLocationResult[]
  >([]);

  // Mission & Preference
  const [mission, setMission] = useState<LogisticsMission>({
    originId: DEFAULT_ORIGIN_ID,
    destinationId: DEFAULT_DESTINATION_ID,
    goods: 'Medical Supplies',
    quantityKg: 1200,
    priority: 'High',
    vehicle: '4×4',
  });
  const [routePreference, setRoutePreference] =
    useState<RoutePreference>('balanced');

  // Routes
  const [routes, setRoutes] = useState<RouteAlternative[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<string>('');
  const [routeError, setRouteError] = useState<RouteErrorState | null>(null);

  // Demand Zones
  const [demandZonesData, setDemandZonesData] =
    useState<DemandZonesResponse | null>(null);
  const [isDemandZonesLoading, setIsDemandZonesLoading] =
    useState<boolean>(false);
  const [demandZonesError, setDemandZonesError] =
    useState<DemandZoneErrorState | null>(null);
  const [showDemandZonesOverlay, setShowDemandZonesOverlay] =
    useState<boolean>(false);
  const [demandClusterCount, setDemandClusterCount] = useState<number>(4);

  // Active Disruption Advisories
  const [alerts, setAlerts] = useState<DisasterAlert[]>([]);

  const originPoint = convertGeocodedToLocationPoint(originGeo);
  const destinationPoint = convertGeocodedToLocationPoint(destinationGeo);

  const selectedRoute =
    routes.find((r) => r.id === selectedRouteId) || routes[0] || null;
  const recommendedRoute = routes[0] || null;

  const handleSelectOriginGeo = (item: GeocodedLocationResult) => {
    setOriginGeo(item);
    setMission((prev) => ({ ...prev, originId: item.place_id }));
  };

  const handleSelectDestinationGeo = (item: GeocodedLocationResult) => {
    setDestinationGeo(item);
    setMission((prev) => ({ ...prev, destinationId: item.place_id }));
  };

  const handleSwapEndpoints = () => {
    const prevOrig = originGeo;
    const prevDest = destinationGeo;
    setOriginGeo(prevDest);
    setDestinationGeo(prevOrig);
    setMission((prev) => ({
      ...prev,
      originId: prevDest.place_id,
      destinationId: prevOrig.place_id,
    }));
  };

  const loadDemandZones = useCallback(
    async (nClusters: number, randomState: number = 42) => {
      setIsDemandZonesLoading(true);
      setDemandZonesError(null);
      try {
        const res = await fetchDemandZones(nClusters, randomState);
        setDemandZonesData(res);
        setDemandClusterCount(res.n_clusters);
      } catch (err: unknown) {
        setDemandZonesData(null);
        if (err instanceof DemandZoneApiError) {
          setDemandZonesError({
            code: err.code,
            title: err.title,
            detail: err.detail,
            status: err.status,
          });
        } else {
          setDemandZonesError({
            code: 'api_error',
            title: 'Demand-Zone Request Failed',
            detail:
              err instanceof Error
                ? err.message
                : 'Unexpected error loading demand zones.',
            status: null,
          });
        }
      } finally {
        setIsDemandZonesLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    let cancelled = false;
    fetchGovernmentDisasterAlerts(selectedRoute).then((res) => {
      if (!cancelled) {
        setAlerts(res.alerts);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [selectedRoute]);

  const executeMissionCalculation = useCallback(
    async (
      origGeo: GeocodedLocationResult,
      destGeo: GeocodedLocationResult,
      currentMission: LogisticsMission,
      currentPreference: RoutePreference
    ) => {
      setAppStage('calculating');
      setRouteError(null);

      const origPt = convertGeocodedToLocationPoint(origGeo);
      const destPt = convertGeocodedToLocationPoint(destGeo);

      try {
        const calculatedRoutes = await calculateRouteAlternatives(
          origPt,
          destPt,
          currentPreference,
          currentMission.priority
        );
        setRoutes(calculatedRoutes);
        const primary = calculatedRoutes[0] || null;
        if (primary) {
          setSelectedRouteId(primary.id);
        }
        setAppStage('workspace');
      } catch (err: unknown) {
        setRoutes([]);
        setSelectedRouteId('');
        if (err instanceof RouteApiError) {
          setRouteError({
            code: err.code,
            title: err.title,
            detail: err.detail,
            status: err.status,
          });
        } else {
          setRouteError({
            code: 'api_error',
            title: 'Route Calculation Failed',
            detail:
              err instanceof Error
                ? err.message
                : 'An unexpected error occurred while calculating routes.',
            status: null,
          });
        }
        setAppStage('workspace');
      }
    },
    []
  );

  const handlePreferenceChange = useCallback(
    (newPref: RoutePreference) => {
      setRoutePreference(newPref);
      setRoutes((prevRoutes) => {
        if (prevRoutes.length === 0) return prevRoutes;
        const reRanked = evaluateAndRankRoutes(
          prevRoutes,
          newPref,
          mission.priority
        );
        if (reRanked.length > 0) {
          setSelectedRouteId(reRanked[0].id);
        }
        return reRanked;
      });
    },
    [mission.priority]
  );

  useEffect(() => {
    let active = true;
    fetchDefaultLocationSuggestions().then((sugs) => {
      if (!active) return;
      setLocationSuggestions(sugs);
      const origMatch = sugs.find((s) => s.place_id === DEFAULT_ORIGIN_ID);
      const destMatch = sugs.find((s) => s.place_id === DEFAULT_DESTINATION_ID);
      if (origMatch) setOriginGeo(origMatch);
      if (destMatch) setDestinationGeo(destMatch);
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadDemandZones(4, 42);
    }, 50);
    return () => clearTimeout(timer);
  }, [loadDemandZones]);

  const refreshAccessibilityData = useCallback(async () => {
    try {
      const [segs, incs] = await Promise.all([
        fetchRoadSegments(),
        fetchIncidents(),
      ]);
      setRoadSegments(segs);
      setFieldIncidents(incs);
    } catch (e) {
      console.warn('Failed to load accessibility data:', e);
    }
  }, []);

  useEffect(() => {
    refreshAccessibilityData();
  }, [refreshAccessibilityData]);

  const refreshTrackingData = useCallback(async () => {
    try {
      const [vList, dList] = await Promise.all([
        fetchVehicles(),
        fetchDeliveries(),
      ]);
      setVehicles(vList);
      setDeliveries(dList);
    } catch (e) {
      console.warn('Failed to load tracking data:', e);
    }
  }, []);

  useEffect(() => {
    refreshTrackingData();
  }, [refreshTrackingData]);

  const refreshNotificationCount = useCallback(async () => {
    try {
      const cnt = await fetchUnreadCount();
      setUnreadAlertCount(cnt);
    } catch (e) {
      console.warn('Failed to fetch unread alert count:', e);
    }
  }, []);

  useEffect(() => {
    refreshNotificationCount();
  }, [refreshNotificationCount]);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    const unsubscribe = subscribeToOfflineQueue((drafts) => {
      setOfflineDraftsCount(drafts.length);
    });

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      unsubscribe();
    };
  }, []);

  const originShort = originGeo.name.split(' (')[0];
  const destShort = destinationGeo.name.split(' (')[0];
  const isSameEndpoint =
    originGeo.place_id === destinationGeo.place_id ||
    Math.hypot(originGeo.lat - destinationGeo.lat, originGeo.lng - destinationGeo.lng) < 0.0005;
  const isOutOfCoverage =
    !originGeo.coverage.within_loaded_graph ||
    !destinationGeo.coverage.within_loaded_graph;

  // ============================================================================
  // SCREEN 1: MINIMALIST WELCOME
  // ============================================================================
  if (appStage === 'welcome') {
    return (
      <div className="min-h-screen w-screen bg-[#090a0f] text-white flex flex-col justify-between px-6 py-8 select-none">
        {/* Top Wordmark */}
        <header className="max-w-5xl w-full mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg overflow-hidden flex items-center justify-center">
              <img src="/favicon.svg" alt="NER SmartRoute" className="w-7 h-7 object-contain" />
            </div>
            <span className="text-sm font-semibold tracking-tight text-white">
              {t.brandTitle}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-medium text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
              title="Toggle Language / भाषा बदलें"
            >
              <Globe className="w-3.5 h-3.5 text-zinc-400" />
              <span>{language === 'en' ? 'हिन्दी (HI)' : 'English (EN)'}</span>
            </button>
            <span className="text-xs text-zinc-500 hidden sm:inline">Meghalaya · NER</span>
          </div>
        </header>

        {/* Centered Hero */}
        <main className="max-w-xl w-full mx-auto text-center space-y-8 animate-wizard-enter">
          {/* Subtle Route Line Graphic */}
          <div className="flex justify-center">
            <svg
              width="120"
              height="44"
              viewBox="0 0 120 44"
              fill="none"
              className="text-zinc-700"
            >
              <path
                d="M12 32 C 42 32, 48 12, 78 12 C 94 12, 102 22, 108 22"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeDasharray="4 4"
              />
              <circle cx="12" cy="32" r="4" className="fill-emerald-400" />
              <circle cx="108" cy="22" r="4" className="fill-blue-400" />
            </svg>
          </div>

          <div className="space-y-3">
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-white leading-snug">
              {t.welcomeTitle}
            </h1>
            <p className="text-sm sm:text-base text-zinc-400 max-w-md mx-auto leading-relaxed">
              {t.welcomeSubtitle}
            </p>
          </div>

          <div>
            <button
              type="button"
              onClick={() => setAppStage('endpoints')}
              className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-white hover:bg-zinc-200 text-zinc-950 font-medium text-sm transition-all cursor-pointer shadow-lg shadow-white/5"
            >
              <span>{t.planRouteButton}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </main>

        {/* Quiet Footer */}
        <footer className="max-w-5xl w-full mx-auto text-center text-xs text-zinc-600">
          OpenStreetMap Road Network · SIH 26002
        </footer>
      </div>
    );
  }

  // ============================================================================
  // SCREEN 2: ORIGIN & DESTINATION
  // ============================================================================
  if (appStage === 'endpoints') {
    return (
      <div className="min-h-screen w-screen bg-[#090a0f] text-white flex flex-col justify-between px-6 py-8">
        <header className="max-w-xl w-full mx-auto flex items-center justify-between">
          <button
            type="button"
            onClick={() => setAppStage('welcome')}
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back</span>
          </button>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[11px] font-medium text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
              title="Toggle Language / भाषा बदलें"
            >
              <Globe className="w-3 h-3 text-zinc-400" />
              <span>{language === 'en' ? 'हिन्दी' : 'EN'}</span>
            </button>
            <span className="text-xs font-medium text-zinc-500">Step 1 of 2</span>
          </div>
        </header>

        <main className="max-w-xl w-full mx-auto my-auto py-6 space-y-6 animate-wizard-enter">
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight text-white">
              Where are you going?
            </h2>
            <p className="text-sm text-zinc-400">
              Choose your starting point and destination.
            </p>
          </div>

          <div className="space-y-2.5 relative">
            <LocationSearchInput
              label="From"
              dotColor="emerald"
              selectedLocation={originGeo}
              suggestions={locationSuggestions}
              onSelectLocation={handleSelectOriginGeo}
            />

            <div className="flex justify-center -my-1 relative z-10">
              <button
                type="button"
                onClick={handleSwapEndpoints}
                title="Swap locations"
                className="p-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-800 transition-colors cursor-pointer"
              >
                <ArrowUpDown className="w-3.5 h-3.5" />
              </button>
            </div>

            <LocationSearchInput
              label="To"
              dotColor="blue"
              selectedLocation={destinationGeo}
              suggestions={locationSuggestions}
              onSelectLocation={handleSelectDestinationGeo}
            />
          </div>

          {isSameEndpoint && (
            <div className="px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 leading-relaxed">
              Starting point and destination cannot be the same location. Please choose two different points.
            </div>
          )}

          {isOutOfCoverage && !isSameEndpoint && (
            <div className="px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 leading-relaxed space-y-2">
              <div className="flex items-center justify-between gap-3">
                <span>
                  {!originGeo.coverage.within_loaded_graph
                    ? originGeo.coverage.message
                    : destinationGeo.coverage.message}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setOriginGeo(buildInitialGeocodedLocation(DEFAULT_ORIGIN_ID));
                    setDestinationGeo(buildInitialGeocodedLocation(DEFAULT_DESTINATION_ID));
                  }}
                  className="shrink-0 px-2.5 py-1 rounded-lg bg-amber-400/20 hover:bg-amber-400/30 text-amber-200 font-medium cursor-pointer"
                >
                  Reset to Shillong → Sohra
                </button>
              </div>
              {(originGeo.coverage.acquire_command || destinationGeo.coverage.acquire_command) && (
                <div className="font-mono text-[11px] text-amber-200/90 bg-zinc-950/70 px-2.5 py-1.5 rounded-lg border border-amber-500/20">
                  {originGeo.coverage.acquire_command || destinationGeo.coverage.acquire_command}
                </div>
              )}
            </div>
          )}

          <div className="pt-2 flex justify-end">
            <button
              type="button"
              disabled={isSameEndpoint || isOutOfCoverage}
              onClick={() => setAppStage('details')}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-white hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-500 text-zinc-950 font-medium text-sm transition-all cursor-pointer disabled:cursor-not-allowed"
            >
              <span>Continue</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </main>

        <div className="h-4" />
      </div>
    );
  }

  // ============================================================================
  // SCREEN 3: PREFERENCES & DETAILS
  // ============================================================================
  if (appStage === 'details') {
    return (
      <div className="min-h-screen w-screen bg-[#090a0f] text-white flex flex-col justify-between px-6 py-8">
        <header className="max-w-xl w-full mx-auto flex items-center justify-between">
          <button
            type="button"
            onClick={() => setAppStage('endpoints')}
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>
              {originShort} → {destShort}
            </span>
          </button>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[11px] font-medium text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
              title="Toggle Language / भाषा बदलें"
            >
              <Globe className="w-3 h-3 text-zinc-400" />
              <span>{language === 'en' ? 'हिन्दी' : 'EN'}</span>
            </button>
            <span className="text-xs font-medium text-zinc-500">Step 2 of 2</span>
          </div>
        </header>

        <main className="max-w-xl w-full mx-auto my-auto py-6 space-y-6 animate-wizard-enter">
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight text-white">
              Route preferences
            </h2>
            <p className="text-sm text-zinc-400">
              Select how routes should be ranked and specify your dispatch details.
            </p>
          </div>

          {/* Optimization Priority Cards */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-400 block">
              Optimization priority
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {(
                [
                  {
                    id: 'balanced',
                    title: 'Balanced',
                    desc: 'Weights distance (45%), time (45%) & road class (10%)',
                  },
                  {
                    id: 'fastest',
                    title: 'Fastest time',
                    desc: 'Minimizes static estimated travel duration',
                  },
                  {
                    id: 'shortest',
                    title: 'Shortest distance',
                    desc: 'Minimizes total physical road length',
                  },
                  {
                    id: 'accessibility',
                    title: 'Accessibility-focused',
                    desc: 'Prioritizes arterial highways (40%) + time + distance',
                  },
                ] as { id: RoutePreference; title: string; desc: string }[]
              ).map((opt) => {
                const active = routePreference === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setRoutePreference(opt.id)}
                    className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer ${
                      active
                        ? 'bg-white text-zinc-950 border-white'
                        : 'bg-zinc-900/90 text-white border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div className="text-sm font-semibold">{opt.title}</div>
                    <div
                      className={`text-xs mt-1 leading-snug ${
                        active ? 'text-zinc-600' : 'text-zinc-400'
                      }`}
                    >
                      {opt.desc}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Compact Cargo & Vehicle Row */}
          <div className="bg-zinc-900/90 border border-zinc-800/90 rounded-2xl p-4 space-y-4">
            <div className="text-xs font-medium text-zinc-400">
              Dispatch details (optional)
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-[11px] text-zinc-500 block mb-1">
                  Cargo type
                </label>
                <select
                  value={mission.goods}
                  onChange={(e) =>
                    setMission({
                      ...mission,
                      goods: e.target.value as GoodsType,
                    })
                  }
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs font-medium text-white focus:outline-none focus:border-zinc-600"
                >
                  {GOODS_OPTIONS.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] text-zinc-500 block mb-1">
                  Vehicle
                </label>
                <select
                  value={mission.vehicle}
                  onChange={(e) =>
                    setMission({
                      ...mission,
                      vehicle: e.target.value as VehicleType,
                    })
                  }
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs font-medium text-white focus:outline-none focus:border-zinc-600"
                >
                  {VEHICLE_OPTIONS.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] text-zinc-500 block mb-1">
                  Urgency
                </label>
                <select
                  value={mission.priority}
                  onChange={(e) =>
                    setMission({
                      ...mission,
                      priority: e.target.value as PriorityType,
                    })
                  }
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs font-medium text-white focus:outline-none focus:border-zinc-600"
                >
                  {PRIORITY_OPTIONS.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setAppStage('endpoints')}
              className="px-4 py-3 rounded-xl text-xs font-medium text-zinc-400 hover:text-white transition-colors cursor-pointer"
            >
              Back
            </button>

            <button
              type="button"
              onClick={() =>
                executeMissionCalculation(
                  originGeo,
                  destinationGeo,
                  mission,
                  routePreference
                )
              }
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-white hover:bg-zinc-200 text-zinc-950 font-medium text-sm transition-all cursor-pointer"
            >
              <span>Calculate route</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </main>

        <div className="h-4" />
      </div>
    );
  }

  // ============================================================================
  // SCREEN 4: QUIET LOADING TRANSITION
  // ============================================================================
  if (appStage === 'calculating') {
    return (
      <div className="min-h-screen w-screen bg-[#090a0f] text-white flex flex-col items-center justify-center px-6">
        <div className="text-center space-y-3 animate-wizard-enter">
          <Loader2 className="w-6 h-6 text-zinc-400 animate-spin mx-auto" />
          <div className="text-sm font-medium text-white">
            Calculating route from {originShort} to {destShort}...
          </div>
          <div className="text-xs text-zinc-500">
            Evaluating road network paths
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // SCREEN 5: CLEAN MAP + ESSENTIAL SIDE SHEET
  // ============================================================================
  const activeEval = selectedRoute?.evaluation ?? recommendedRoute?.evaluation;

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col lg:flex-row bg-slate-100 select-none animate-workspace-reveal">
      {/* Left/Main Area: Full-Bleed Interactive Map */}
      <div className="w-full h-[52vh] lg:h-full lg:flex-1 relative bg-slate-200">
        <MapView
          origin={originPoint}
          destination={destinationPoint}
          routes={routes}
          selectedRouteId={selectedRouteId}
          onSelectRoute={(id) => setSelectedRouteId(id)}
          facilities={DEFAULT_FACILITIES}
          activeInfraCategories={DEFAULT_ACTIVE_INFRA}
          alerts={alerts}
          radar={INITIAL_RADAR}
          onToggleRadarActive={() => {}}
          onToggleRadarPlay={() => {}}
          onStepRadarFrame={() => {}}
          onRetryRadar={() => {}}
          focusTarget={focusTarget}
          routeError={routeError}
          demandZones={demandZonesData}
          showDemandZones={showDemandZonesOverlay}
          roadSegments={roadSegments}
          fieldIncidents={fieldIncidents}
          showAccessibilityOverlay={true}
          vehicles={vehicles}
          deliveries={deliveries}
          showVehiclesOverlay={true}
        />

        {/* Floating Unified GIS Intelligence Status Pill */}
        <div className="absolute top-4 left-4 z-[1000] hidden md:flex items-center gap-2 bg-white/95 backdrop-blur-md px-3.5 py-1.5 rounded-xl shadow-lg border border-slate-200/80 text-xs text-slate-700 select-none">
          <div className="flex items-center gap-1.5 font-bold text-slate-900">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>NER GIS</span>
          </div>
          <span className="text-slate-300">·</span>
          <span>21,764 OSM Nodes</span>
          <span className="text-slate-300">·</span>
          <span>{alerts.length} Advisories</span>
          <span className="text-slate-300">·</span>
          <span>{vehicles.length} Fleet</span>
          <span className="text-slate-300">·</span>
          <span className="flex items-center gap-1">
            {isOnline ? (
              <span className="text-emerald-700 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> {t.online}
              </span>
            ) : (
              <span className="text-amber-700 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> {t.offline} ({offlineDraftsCount})
              </span>
            )}
          </span>
        </div>
      </div>

      {/* Right Area: Minimalist Side Sheet */}
      <aside className="w-full h-[48vh] lg:h-full lg:w-[400px] xl:w-[420px] bg-white border-t lg:border-t-0 lg:border-l border-slate-200 flex flex-col z-20 animate-panel-enter">
        {/* Sheet Header */}
        <div className="px-4 py-3.5 border-b border-slate-100 flex items-center justify-between shrink-0">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
              <span>{t.recommendedRoute}</span>
              <span>·</span>
              <span>{mission.vehicle}</span>
            </div>
            <h2 className="text-base font-semibold text-slate-900 truncate mt-0.5">
              {originShort} → {destShort}
            </h2>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            {/* Language Toggle */}
            <button
              type="button"
              onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
              className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-colors border border-slate-200 cursor-pointer"
              title="Toggle Language / भाषा बदलें"
            >
              <Globe className="w-3.5 h-3.5 text-slate-600" />
              <span>{language === 'en' ? 'हिन्दी' : 'EN'}</span>
            </button>

            {/* Offline Sync Queue */}
            <button
              type="button"
              onClick={() => setIsOfflineQueueOpen(true)}
              className={`relative inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors border cursor-pointer ${
                offlineDraftsCount > 0
                  ? 'bg-amber-50 hover:bg-amber-100 text-amber-800 border-amber-300'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'
              }`}
              title="Offline Drafts & Sync Queue"
            >
              {isOnline ? (
                <Wifi className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <WifiOff className="w-3.5 h-3.5 text-amber-600" />
              )}
              {offlineDraftsCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-amber-500 text-white font-mono text-[9px] font-bold flex items-center justify-center -mr-0.5">
                  {offlineDraftsCount}
                </span>
              )}
            </button>

            {/* Alerts Center */}
            <button
              type="button"
              onClick={() => setIsNotificationModalOpen(true)}
              className="relative inline-flex items-center gap-1 px-2 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors cursor-pointer"
              title="Operational Alerts & Notification Center"
            >
              <Bell className="w-3.5 h-3.5 text-slate-700" />
              {unreadAlertCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-rose-500 text-white font-mono text-[9px] font-bold flex items-center justify-center -mr-0.5">
                  {unreadAlertCount}
                </span>
              )}
            </button>

            {/* Cargo Dispatch */}
            <button
              type="button"
              onClick={() => setIsNewDeliveryModalOpen(true)}
              className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg bg-sky-50 hover:bg-sky-100 text-sky-700 text-xs font-medium transition-colors border border-sky-200 cursor-pointer"
              title="Dispatch cargo delivery along active route"
            >
              <Truck className="w-3.5 h-3.5 text-sky-600" />
            </button>

            {/* Field Incident Report */}
            <button
              type="button"
              onClick={() => setIsFieldReportModalOpen(true)}
              className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-medium transition-colors border border-rose-200 cursor-pointer"
              title="Report road blockage, landslide, or damage"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
            </button>

            {/* Change Endpoints */}
            <button
              type="button"
              onClick={() => setAppStage('endpoints')}
              className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors cursor-pointer"
              title={t.changeRoute}
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Scrollable Sheet Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5 custom-scrollbar">
          {/* Priority Switcher */}
          <div className="grid grid-cols-4 gap-1 p-1 bg-slate-100 rounded-xl">
            {(
              [
                { id: 'balanced', label: 'Balanced' },
                { id: 'fastest', label: 'Fastest' },
                { id: 'shortest', label: 'Shortest' },
                { id: 'accessibility', label: 'Access' },
              ] as { id: RoutePreference; label: string }[]
            ).map((pref) => {
              const active = routePreference === pref.id;
              return (
                <button
                  key={pref.id}
                  type="button"
                  onClick={() => handlePreferenceChange(pref.id)}
                  className={`py-1.5 px-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                    active
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {pref.label}
                </button>
              );
            })}
          </div>

          {/* Error State */}
          {routeError && (
            <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-200/80 space-y-2.5">
              <div className="flex items-center gap-2 text-amber-900 font-semibold text-sm">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>{routeError.title}</span>
              </div>
              <p className="text-xs text-amber-800 leading-relaxed">
                {routeError.detail}
              </p>
              <div className="pt-1 flex gap-2">
                <button
                  type="button"
                  onClick={() =>
                    executeMissionCalculation(
                      originGeo,
                      destinationGeo,
                      mission,
                      routePreference
                    )
                  }
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-medium cursor-pointer"
                >
                  Retry calculation
                </button>
                <button
                  type="button"
                  onClick={() => setAppStage('endpoints')}
                  className="px-3.5 py-1.5 rounded-lg bg-white border border-amber-300 text-amber-900 text-xs font-medium cursor-pointer"
                >
                  Choose another location
                </button>
              </div>
            </div>
          )}

          {/* Primary Route Metrics & Candidates */}
          {!routeError && selectedRoute && (
            <>
              {/* Key Numbers for Selected Route */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-500">
                    {selectedRoute.name.split(' (')[0]}
                  </span>
                  <span
                    className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                      selectedRoute.status === 'RECOMMENDED'
                        ? 'bg-blue-50 text-blue-700'
                        : 'bg-slate-200/70 text-slate-600'
                    }`}
                  >
                    {selectedRoute.status === 'RECOMMENDED'
                      ? 'Recommended'
                      : 'Alternative'}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 pt-1">
                  <div>
                    <div className="text-base sm:text-lg font-semibold text-slate-900 leading-tight">
                      {formatDurationHoursMinutes(selectedRoute.durationMinutes)}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Est. time
                    </div>
                  </div>

                  <div>
                    <div className="text-base sm:text-lg font-semibold text-slate-900 leading-tight">
                      {selectedRoute.distanceKm}{' '}
                      <span className="text-xs font-normal text-slate-500">
                        km
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Distance
                    </div>
                  </div>

                  <div>
                    <div className="text-base sm:text-lg font-semibold text-blue-600 leading-tight">
                      {activeEval?.weightedScore ?? selectedRoute.logisticsScore}
                      <span className="text-xs font-normal text-slate-400">
                        /100
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Score
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed pt-2 border-t border-slate-200/60">
                  {activeEval?.tradeoffNote || selectedRoute.tradeoffs}
                </p>

                {/* Weather & Disruptions Intelligence Row */}
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200/60">
                  <div className="p-2 rounded-xl bg-white border border-slate-200/80 space-y-0.5 text-left">
                    <div className="text-[10px] text-slate-400 font-medium">Corridor Weather</div>
                    <div className="text-xs font-semibold text-slate-800 truncate">
                      {selectedRoute.weather?.corridor_metrics
                        ? `${selectedRoute.weather.corridor_metrics.mean_temperature_c}°C · ${selectedRoute.weather.corridor_metrics.max_rain_probability_pct}% rain`
                        : 'Open-Meteo model'}
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      {selectedRoute.weather?.guidance ?? 'Live numerical forecast'}
                    </div>
                  </div>

                  <div className="p-2 rounded-xl bg-white border border-slate-200/80 space-y-0.5 text-left">
                    <div className="text-[10px] text-slate-400 font-medium">Road Advisories</div>
                    <div className="text-xs font-semibold text-slate-800 truncate">
                      {selectedRoute.disruptions?.status === 'clear'
                        ? '100% Clear Corridor'
                        : `${selectedRoute.disruptions?.intersected_count ?? 0} Active Advisory`}
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      {selectedRoute.disruptions?.explanation ?? 'Verified NHIDCL/PWD advisories'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Route Candidates Selector */}
              <div className="space-y-2">
                <div className="text-xs font-medium text-slate-400">
                  Available routes ({routes.length})
                </div>
                <div className="space-y-2">
                  {routes.map((route) => {
                    const isSelected = route.id === selectedRouteId;
                    const ev = route.evaluation;
                    return (
                      <button
                        key={route.id}
                        type="button"
                        onClick={() => setSelectedRouteId(route.id)}
                        className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                          isSelected
                            ? 'bg-blue-50/40 border-blue-500'
                            : 'bg-white border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: route.color }}
                          />
                          <div className="min-w-0">
                            <div className="text-xs font-semibold text-slate-900 truncate">
                              {route.name.split(' (')[0]}
                            </div>
                            <div className="text-[11px] text-slate-500 mt-0.5">
                              {route.distanceKm} km ·{' '}
                              {formatDurationHoursMinutes(route.durationMinutes)}{' '}
                              est.
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className="text-xs font-semibold text-slate-900">
                            {ev?.weightedScore ?? route.logisticsScore}
                          </span>
                          <span className="text-[11px] text-slate-400">/100</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Progressive Drawer 1: Score Breakdown */}
              <div className="border-t border-slate-100 pt-3">
                <button
                  type="button"
                  onClick={() => setShowScoreDetails((prev) => !prev)}
                  className="w-full py-1.5 flex items-center justify-between text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
                >
                  <span>Score breakdown & road quality</span>
                  {showScoreDetails ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </button>

                {showScoreDetails && activeEval && (
                  <div className="mt-3 p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-3 text-xs animate-step-enter">
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between text-slate-600 mb-1">
                          <span>Distance efficiency</span>
                          <span className="font-medium text-slate-900">
                            {activeEval.distanceScore}/100
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-600 rounded-full"
                            style={{ width: `${activeEval.distanceScore}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-slate-600 mb-1">
                          <span>Estimated time efficiency</span>
                          <span className="font-medium text-slate-900">
                            {activeEval.timeScore}/100
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-600 rounded-full"
                            style={{ width: `${activeEval.timeScore}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-slate-600 mb-1">
                          <span>Road hierarchy quality</span>
                          <span className="font-medium text-slate-900">
                            {activeEval.roadHierarchyScore}/100
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-indigo-600 rounded-full"
                            style={{
                              width: `${activeEval.roadHierarchyScore}%`,
                            }}
                          />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-slate-600 mb-1">
                          <span>Endpoint snap quality</span>
                          <span className="font-medium text-slate-900">
                            {activeEval.snapQualityScore}/100
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-teal-600 rounded-full"
                            style={{ width: `${activeEval.snapQualityScore}%` }}
                          />
                        </div>
                      </div>

                      {typeof activeEval.weatherExposureScore === 'number' && (
                        <div>
                          <div className="flex justify-between text-slate-600 mb-1">
                            <span>Weather corridor safety</span>
                            <span className="font-medium text-slate-900">
                              {activeEval.weatherExposureScore}/100
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-sky-600 rounded-full"
                              style={{ width: `${activeEval.weatherExposureScore}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {typeof activeEval.confirmedDisruptionsScore === 'number' && (
                        <div>
                          <div className="flex justify-between text-slate-600 mb-1">
                            <span>Disruption-free corridor score</span>
                            <span className="font-medium text-slate-900">
                              {activeEval.confirmedDisruptionsScore}/100
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-600 rounded-full"
                              style={{ width: `${activeEval.confirmedDisruptionsScore}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>

                    {activeEval.advantages.length > 0 && (
                      <div className="pt-2 border-t border-slate-200/70 space-y-1">
                        <div className="text-[11px] font-medium text-emerald-700">
                          Why selected / Strengths
                        </div>
                        {activeEval.advantages.slice(0, 3).map((adv, idx) => (
                          <div
                            key={idx}
                            className="text-[11px] text-slate-600 leading-snug"
                          >
                            + {adv}
                          </div>
                        ))}
                      </div>
                    )}

                    {activeEval.disadvantages.length > 0 && (
                      <div className="pt-1.5 space-y-1">
                        <div className="text-[11px] font-medium text-amber-700">
                          Trade-offs / Limitations
                        </div>
                        {activeEval.disadvantages.slice(0, 3).map((dis, idx) => (
                          <div
                            key={idx}
                            className="text-[11px] text-slate-600 leading-snug"
                          >
                            − {dis}
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="pt-2 border-t border-slate-200/70 flex items-center justify-between text-[11px] text-slate-500">
                      <span>
                        Arterial: {activeEval.roadClassBreakdownPct.major_arterial}%
                      </span>
                      <span>
                        Collector:{' '}
                        {activeEval.roadClassBreakdownPct.secondary_collector}%
                      </span>
                      <span>
                        Avg speed: {activeEval.impliedAvgSpeedKmh} km/h
                      </span>
                    </div>

                    <div className="pt-2 border-t border-slate-200/70 space-y-1 text-[11px] text-slate-500">
                      <div className="font-medium text-slate-600">
                        Unavailable metrics (excluded from score)
                      </div>
                      {typeof activeEval.weatherExposureScore !== 'number' && (
                        <div>• Weather exposure: Atmospheric station unreachable</div>
                      )}
                      {typeof activeEval.confirmedDisruptionsScore !== 'number' && (
                        <div>• Confirmed road disruptions: Advisory feed unreachable</div>
                      )}
                      <div>• Live traffic telemetry: Unavailable in backend dataset</div>
                    </div>

                    <div className="text-[11px] text-slate-400 leading-normal">
                      Formula: {PREFERENCE_CONFIGS[routePreference].formulaText}. Provenance: {selectedRoute.source}.
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Progressive Drawer 2: Demand Zones Overlay */}
          <div className="border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => {
                setShowDemandSection((prev) => {
                  const next = !prev;
                  if (next && !demandZonesData && !isDemandZonesLoading) {
                    loadDemandZones(demandClusterCount, 42);
                  }
                  return next;
                });
              }}
              className="w-full py-1.5 flex items-center justify-between text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
            >
              <span>Demand zones overlay (K-Means)</span>
              {showDemandSection ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </button>

            {showDemandSection && (
              <div className="mt-3 p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-3 text-xs animate-step-enter">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700">
                    Show 40 demand points on map
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setShowDemandZonesOverlay((prev) => !prev)
                    }
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                      showDemandZonesOverlay
                        ? 'bg-slate-900 text-white'
                        : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                    }`}
                  >
                    {showDemandZonesOverlay ? 'Visible' : 'Hidden'}
                  </button>
                </div>

                {/* Cluster Count Selector */}
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Clusters (K)</span>
                  <div className="flex gap-1">
                    {[2, 3, 4, 5, 6].map((k) => (
                      <button
                        key={k}
                        type="button"
                        disabled={isDemandZonesLoading}
                        onClick={() => {
                          setDemandClusterCount(k);
                          loadDemandZones(k, 42);
                        }}
                        className={`w-7 h-7 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                          demandClusterCount === k
                            ? 'bg-slate-900 text-white'
                            : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                        }`}
                      >
                        {k}
                      </button>
                    ))}
                  </div>
                </div>

                {demandZonesError && (
                  <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 space-y-2">
                    <p>{demandZonesError.detail}</p>
                    <button
                      type="button"
                      onClick={() => loadDemandZones(demandClusterCount, 42)}
                      disabled={isDemandZonesLoading}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-600 text-white font-medium hover:bg-rose-700 disabled:opacity-50 cursor-pointer"
                    >
                      {isDemandZonesLoading ? 'Connecting...' : 'Retry loading demand zones'}
                    </button>
                  </div>
                )}

                {isDemandZonesLoading && !demandZonesData && !demandZonesError && (
                  <div className="py-2 text-center text-xs text-slate-500 animate-pulse">
                    Computing K-Means demand zones (EPSG:32646)...
                  </div>
                )}

                {demandZonesData && (
                  <>
                    <div className="space-y-1.5 pt-1">
                      {demandZonesData.clusters.map((c) => (
                        <button
                          key={c.cluster_id}
                          type="button"
                          onClick={() => {
                            if (!showDemandZonesOverlay) {
                              setShowDemandZonesOverlay(true);
                            }
                            setFocusTarget([c.center_lat, c.center_lng]);
                          }}
                          className="w-full text-left px-2.5 py-1.5 rounded-lg bg-white border border-slate-200/80 hover:border-slate-300 flex items-center justify-between text-[11px] cursor-pointer"
                        >
                          <span className="flex items-center gap-2 font-medium text-slate-700">
                            <span
                              className="w-2 h-2 rounded-full"
                              style={{
                                backgroundColor: getClusterColor(c.cluster_id),
                              }}
                            />
                            Zone #{c.cluster_id} ({c.point_count} pts)
                          </span>
                          <span className="text-slate-500">
                            {c.total_demand_units.toFixed(0)} units
                          </span>
                        </button>
                      ))}
                    </div>

                    <div className="flex justify-between text-[11px] text-slate-500 pt-1">
                      <span>
                        Silhouette:{' '}
                        {demandZonesData.evaluation_metrics.silhouette_score?.toFixed(
                          3
                        ) ?? 'N/A'}
                      </span>
                      <span>
                        Davies–Bouldin:{' '}
                        {demandZonesData.evaluation_metrics.davies_bouldin_score?.toFixed(
                          3
                        ) ?? 'N/A'}
                      </span>
                    </div>
                  </>
                )}

                <div className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200/70 rounded-lg px-2.5 py-1.5 leading-snug">
                  DEMONSTRATION DATA — SYNTHETIC DEMAND, NOT REAL-WORLD OBSERVATIONS. Internal cohesion metrics only.
                </div>
              </div>
            )}
          </div>

          {/* Progressive Drawer 3: Route-Ranking ML Model */}
          <div className="border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => setShowMlSection((prev) => !prev)}
              className="w-full py-1.5 flex items-center justify-between text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
            >
              <span>Route-ranking AI / ML (Experimental)</span>
              {showMlSection ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </button>

            {showMlSection && (
              <div className="mt-3 p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-3 text-xs animate-step-enter">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800">
                    Pairwise Logistic Ranker v1
                  </span>
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                    GroupShuffleSplit Eval
                  </span>
                </div>

                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Evaluated on 240 query-grouped multi-criteria corridor benchmark scenarios with zero spatial corridor leakage between train (60%), validation (20%), and held-out test (20%).
                </p>

                {/* Candidate win probabilities */}
                {selectedRoute?.mlRanking?.win_probabilities && (
                  <div className="space-y-1.5 pt-1">
                    <div className="text-[11px] font-medium text-slate-700">
                      Candidate Pairwise Win Probabilities (Current Query)
                    </div>
                    {Object.entries(selectedRoute.mlRanking.win_probabilities).map(
                      ([routeKey, prob]) => {
                        const matchingCandidate = routes.find(
                          (r) => r.routeType === routeKey || r.id === routeKey
                        );
                        const label =
                          matchingCandidate?.name.split(' (')[0] ?? routeKey;
                        const pct = Math.round(prob * 100);
                        return (
                          <div key={routeKey} className="space-y-1">
                            <div className="flex justify-between text-[11px] text-slate-600">
                              <span className="truncate">{label}</span>
                              <span className="font-medium text-slate-900">
                                {pct}% win rate
                              </span>
                            </div>
                            <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-indigo-600 rounded-full"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      }
                    )}
                  </div>
                )}

                {/* Held-out test evaluation comparison table */}
                <div className="pt-2 border-t border-slate-200/70 space-y-1.5">
                  <div className="text-[11px] font-medium text-slate-700">
                    Held-Out Test Set Benchmark Comparison (288 Pairs)
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-[10px] text-slate-600">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500 text-left">
                          <th className="pb-1 font-medium">Method</th>
                          <th className="pb-1 text-right font-medium">Pairwise Acc</th>
                          <th className="pb-1 text-right font-medium">NDCG@3</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        <tr className="text-indigo-900 font-semibold bg-indigo-50/50">
                          <td className="py-1">Pairwise ML Ranker</td>
                          <td className="py-1 text-right">98.6%</td>
                          <td className="py-1 text-right">0.999</td>
                        </tr>
                        <tr>
                          <td className="py-1">Deterministic Baseline</td>
                          <td className="py-1 text-right">88.2%</td>
                          <td className="py-1 text-right">0.980</td>
                        </tr>
                        <tr>
                          <td className="py-1">Fastest-Time Heuristic</td>
                          <td className="py-1 text-right">84.0%</td>
                          <td className="py-1 text-right">0.953</td>
                        </tr>
                        <tr>
                          <td className="py-1">Road-Hierarchy Heuristic</td>
                          <td className="py-1 text-right">77.1%</td>
                          <td className="py-1 text-right">0.937</td>
                        </tr>
                        <tr>
                          <td className="py-1">Shortest-Distance Heuristic</td>
                          <td className="py-1 text-right">18.8%</td>
                          <td className="py-1 text-right">0.718</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200/70 rounded-lg px-2.5 py-1.5 leading-snug">
                  SYNTHETIC BENCHMARK PIPELINE — Validates pairwise ranking mathematics and zero-leakage GroupShuffleSplit partitioning. Real-world dispatch recommendations are governed by the explainable multi-criteria formula.
                </div>
              </div>
            )}
          </div>

          {/* Progressive Drawer 4: Road Accessibility & Field Reports (Module D & E) */}
          <div className="border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => setShowAccessibilitySection((prev) => !prev)}
              className="w-full py-1.5 flex items-center justify-between text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />
                <span>Road Accessibility & Field Intelligence</span>
              </span>
              {showAccessibilitySection ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </button>

            {showAccessibilitySection && (
              <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200/70 space-y-3 text-xs animate-step-enter">
                <AccessibilityMonitorPanel
                  onSelectSegment={(seg) => {
                    if (seg.coordinates && seg.coordinates[0]) {
                      setFocusTarget([seg.coordinates[0][0], seg.coordinates[0][1]]);
                    }
                  }}
                  onSelectIncident={(inc) => {
                    setFocusTarget([inc.latitude, inc.longitude]);
                  }}
                  onRequestNewReport={() => setIsFieldReportModalOpen(true)}
                />
              </div>
            )}
          </div>

          {/* Progressive Drawer 5: GPS Fleet & Delivery Tracking (Module F) */}
          <div className="border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={() => setShowTrackingSection((prev) => !prev)}
              className="w-full py-1.5 flex items-center justify-between text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <Truck className="w-3.5 h-3.5 text-sky-600" />
                <span>GPS Fleet & Delivery Tracking</span>
              </span>
              {showTrackingSection ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </button>

            {showTrackingSection && (
              <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200/70 space-y-3 text-xs animate-step-enter">
                <TrackingMonitorPanel
                  onSelectVehicle={(veh) => {
                    if (veh.current_latitude !== null && veh.current_longitude !== null) {
                      setFocusTarget([veh.current_latitude, veh.current_longitude]);
                    }
                  }}
                  onSelectDelivery={(del) => {
                    setFocusTarget([del.origin_lat, del.origin_lng]);
                  }}
                  onRequestNewDelivery={() => setIsNewDeliveryModalOpen(true)}
                />
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Field Report Submission Modal (Module E) */}
      <FieldReportModal
        isOpen={isFieldReportModalOpen}
        onClose={() => setIsFieldReportModalOpen(false)}
        defaultCoords={originGeo ? [originGeo.lat, originGeo.lng] : undefined}
        defaultLocationName={originGeo ? originGeo.name.split(' (')[0] : undefined}
        onReportSubmitted={() => {
          refreshAccessibilityData();
        }}
      />

      {/* Dispatch New Delivery Mission Modal (Module F) */}
      <NewDeliveryModal
        isOpen={isNewDeliveryModalOpen}
        onClose={() => setIsNewDeliveryModalOpen(false)}
        vehicles={vehicles}
        activeRoute={selectedRoute ?? recommendedRoute}
        originName={originShort}
        destinationName={destShort}
        onDeliveryCreated={() => {
          refreshTrackingData();
        }}
      />

      {/* Operational Alerts & Notification Center Modal (Module G) */}
      <NotificationCenterModal
        isOpen={isNotificationModalOpen}
        onClose={() => setIsNotificationModalOpen(false)}
        onFocusLocation={(coords) => setFocusTarget(coords)}
        onUnreadCountChange={(cnt) => setUnreadAlertCount(cnt)}
      />

      {/* Offline Drafts & Sync Queue Modal (Module H / Phase 7) */}
      <OfflineQueueModal
        isOpen={isOfflineQueueOpen}
        onClose={() => setIsOfflineQueueOpen(false)}
        onSyncComplete={() => {
          refreshAccessibilityData();
        }}
      />
    </div>
  );
}

export default App;
