import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { RouteAlternative, RouteErrorState } from '../types/route';
import { LocationPoint } from '../types/mission';
import { CriticalFacility, InfraCategory } from '../types/infrastructure';
import { DisasterAlert } from '../types/alert';
import { RadarState } from '../types/radar';
import { DemandZonesResponse, getClusterColor } from '../types/demandZone';
import { RoadSegment, IncidentReport } from '../types/accessibility';
import { Vehicle, Delivery } from '../types/tracking';
import { getRadarTileUrl } from '../services/radarService';
import { NER_PILOT_BOUNDS, NER_CENTER, NER_DEFAULT_ZOOM } from '../data/locations';
import { formatDurationHoursMinutes } from '../logic/formatters';
import { LocateFixed, Globe } from 'lucide-react';

const FULL_NER_BOUNDS: [[number, number], [number, number]] = [
  [21.9, 88.0],
  [29.5, 97.4],
];

interface MapViewProps {
  routes: RouteAlternative[];
  selectedRouteId: string;
  onSelectRoute: (routeId: string) => void;
  origin: LocationPoint | undefined;
  destination: LocationPoint | undefined;
  facilities: CriticalFacility[];
  activeInfraCategories: InfraCategory[];
  alerts: DisasterAlert[];
  radar: RadarState;
  onToggleRadarActive: () => void;
  onToggleRadarPlay: () => void;
  onStepRadarFrame: (direction: 'next' | 'prev') => void;
  onRetryRadar: () => void;
  focusTarget?: [number, number] | null;
  routeError?: RouteErrorState | null;
  demandZones?: DemandZonesResponse | null;
  showDemandZones?: boolean;
  roadSegments?: RoadSegment[];
  fieldIncidents?: IncidentReport[];
  showAccessibilityOverlay?: boolean;
  vehicles?: Vehicle[];
  deliveries?: Delivery[];
  showVehiclesOverlay?: boolean;
  onStepSimulation?: (deliveryId: string) => void;
}

export const MapView: React.FC<MapViewProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
  origin,
  destination,
  facilities,
  activeInfraCategories,
  alerts,
  radar,
  onToggleRadarActive: _onToggleRadarActive,
  onToggleRadarPlay: _onToggleRadarPlay,
  onStepRadarFrame: _onStepRadarFrame,
  onRetryRadar: _onRetryRadar,
  focusTarget,
  routeError: _routeError = null,
  demandZones = null,
  showDemandZones = true,
  roadSegments = [],
  fieldIncidents = [],
  showAccessibilityOverlay = true,
  vehicles = [],
  deliveries = [],
  showVehiclesOverlay = true,
  onStepSimulation: _onStepSimulation,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  const routesLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const demandZonesLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const accessibilityLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const incidentsLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const vehiclesLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const markersLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const facilitiesLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const alertsLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const radarTileLayerRef = useRef<L.TileLayer | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: NER_CENTER,
      zoom: NER_DEFAULT_ZOOM,
      zoomControl: false,
      attributionControl: true
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
    }).addTo(map);

    L.control.zoom({ position: 'topleft' }).addTo(map);

    routesLayerGroupRef.current = L.layerGroup().addTo(map);
    demandZonesLayerGroupRef.current = L.layerGroup().addTo(map);
    accessibilityLayerGroupRef.current = L.layerGroup().addTo(map);
    incidentsLayerGroupRef.current = L.layerGroup().addTo(map);
    vehiclesLayerGroupRef.current = L.layerGroup().addTo(map);
    markersLayerGroupRef.current = L.layerGroup().addTo(map);
    facilitiesLayerGroupRef.current = L.layerGroup().addTo(map);
    alertsLayerGroupRef.current = L.layerGroup().addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Fit bounds to active route or pilot area
  const handleFocusNER = () => {
    if (!mapRef.current) return;
    if (routes.length > 0) {
      const b = L.latLngBounds([]);
      routes.forEach((r) => r.coordinates.forEach((pt) => b.extend(pt)));
      if (b.isValid()) {
        mapRef.current.fitBounds(b, { padding: [50, 50], maxZoom: 13, animate: true });
        return;
      }
    }
    mapRef.current.fitBounds(NER_PILOT_BOUNDS, {
      padding: [40, 40],
      maxZoom: 12,
      animate: true
    });
  };

  // Fit bounds to all 8 North Eastern states
  const handleFocusFullNER = () => {
    if (!mapRef.current) return;
    mapRef.current.fitBounds(FULL_NER_BOUNDS, {
      padding: [30, 30],
      maxZoom: 7,
      animate: true
    });
  };

  // Fly to target when focusTarget changes
  useEffect(() => {
    if (focusTarget && mapRef.current) {
      mapRef.current.flyTo(focusTarget, 14, { duration: 1.2 });
    }
  }, [focusTarget]);

  // 1. Render Routes
  useEffect(() => {
    if (!mapRef.current || !routesLayerGroupRef.current) return;
    const group = routesLayerGroupRef.current;
    group.clearLayers();

    if (routes.length === 0) return;

    const bounds = L.latLngBounds([]);

    // Draw unselected routes first, selected on top
    const sorted = [...routes].sort((a, b) => {
      if (a.id === selectedRouteId) return 1;
      if (b.id === selectedRouteId) return -1;
      return 0;
    });

    sorted.forEach((route) => {
      const isSelected = route.id === selectedRouteId;

      if (route.coordinates && route.coordinates.length > 0) {
        route.coordinates.forEach(pt => bounds.extend(pt));

        const polyline = L.polyline(route.coordinates, {
          color: isSelected ? '#2563eb' : route.color || '#94a3b8',
          weight: isSelected ? 6 : 4,
          opacity: isSelected ? 0.95 : 0.65,
          dashArray: isSelected ? undefined : '5, 6',
          lineCap: 'round',
          lineJoin: 'round'
        });

        polyline.bindTooltip(
          `<div class="p-1 text-xs">
            <strong class="text-blue-700">${route.name}</strong><br/>
            ${route.distanceKm} km · ${formatDurationHoursMinutes(route.durationMinutes)} (est., imputed speed)<br/>
            <span class="text-slate-600 font-semibold">${route.numNodes ?? route.coordinates.length} road nodes</span>
          </div>`,
          { sticky: true }
        );

        polyline.on('click', () => {
          onSelectRoute(route.id);
        });

        polyline.addTo(group);
      }
    });

    if (bounds.isValid()) {
      mapRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
    }
  }, [routes, selectedRouteId, onSelectRoute]);

  // 2. Render Origin & Destination with Pulsing Animation
  useEffect(() => {
    if (!mapRef.current || !markersLayerGroupRef.current) return;
    const group = markersLayerGroupRef.current;
    group.clearLayers();

    // Origin Marker (Green Pin with ring)
    if (origin) {
      const originIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `
          <div class="relative flex items-center justify-center">
            <span class="animate-ping absolute inline-flex h-7 w-7 rounded-full bg-emerald-400 opacity-75"></span>
            <div class="relative w-8 h-8 rounded-full bg-emerald-600 text-white shadow-lg border-2 border-white flex items-center justify-center">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 10l7-7m0 0l7 7m-7-7v18"/>
              </svg>
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      const originMarker = L.marker([origin.lat, origin.lng], { icon: originIcon });
      originMarker.bindPopup(`
        <div class="text-xs p-1.5 font-sans">
          <div class="font-extrabold text-emerald-800 text-sm">ORIGIN: ${origin.name}</div>
          <div class="text-slate-600 mt-1">${origin.description}</div>
          <div class="mt-1 text-slate-400 font-mono text-[10px]">Elevation: ${origin.elevationMeters}m MSL</div>
        </div>
      `);
      originMarker.addTo(group);
    }

    // Destination Marker (Red Flag Pin with ring)
    if (destination) {
      const destIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `
          <div class="relative flex items-center justify-center">
            <span class="animate-ping absolute inline-flex h-7 w-7 rounded-full bg-rose-400 opacity-75"></span>
            <div class="relative w-8 h-8 rounded-full bg-rose-600 text-white shadow-lg border-2 border-white flex items-center justify-center">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      const destMarker = L.marker([destination.lat, destination.lng], { icon: destIcon });
      destMarker.bindPopup(`
        <div class="text-xs p-1.5 font-sans">
          <div class="font-extrabold text-rose-800 text-sm">DESTINATION: ${destination.name}</div>
          <div class="text-slate-600 mt-1">${destination.description}</div>
          <div class="mt-1 text-slate-400 font-mono text-[10px]">Elevation: ${destination.elevationMeters}m MSL</div>
        </div>
      `);
      destMarker.addTo(group);
    }

    if (origin && destination && routes.length === 0) {
      const markerBounds = L.latLngBounds([
        [origin.lat, origin.lng],
        [destination.lat, destination.lng]
      ]);
      if (markerBounds.isValid()) {
        mapRef.current.fitBounds(markerBounds, { padding: [60, 60], maxZoom: 11 });
      }
    }
  }, [origin, destination, routes.length]);

  // 3. Render Facilities
  useEffect(() => {
    if (!mapRef.current || !facilitiesLayerGroupRef.current) return;
    const group = facilitiesLayerGroupRef.current;
    group.clearLayers();

    const visibleFacilities = facilities.filter(f => activeInfraCategories.includes(f.category));

    visibleFacilities.forEach(facility => {
      let iconColor = '#2563eb';
      let symbol = '■';

      if (facility.category === 'hospital') {
        iconColor = '#f43f5e';
        symbol = '✚';
      } else if (facility.category === 'relief') {
        iconColor = '#f59e0b';
        symbol = '▲';
      }

      const icon = L.divIcon({
        className: 'custom-div-icon',
        html: `
          <div class="flex items-center justify-center w-6 h-6 rounded-full text-white font-black text-[10px] shadow-md border-2 border-white hover:scale-110 transition-transform" style="background-color: ${iconColor};">
            ${symbol}
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      const marker = L.marker([facility.lat, facility.lng], { icon });
      marker.bindPopup(`
        <div class="text-xs p-1.5 max-w-[210px] font-sans">
          <div class="font-extrabold text-slate-900">${facility.name}</div>
          <div class="text-[10px] uppercase font-bold mt-0.5" style="color: ${iconColor}">${facility.category}</div>
          <div class="text-slate-600 mt-1 text-[11px]">${facility.address}</div>
          <div class="mt-1 font-semibold text-slate-800 text-[11px]">${facility.capacityOrType}</div>
        </div>
      `);
      marker.addTo(group);
    });
  }, [facilities, activeInfraCategories]);

  // 4. Render Active Alerts Hazard Zones
  useEffect(() => {
    if (!mapRef.current || !alertsLayerGroupRef.current) return;
    const group = alertsLayerGroupRef.current;
    group.clearLayers();

    alerts.forEach(alert => {
      if (alert.lat && alert.lng) {
        const circle = L.circle([alert.lat, alert.lng], {
          radius: (alert.radiusKm || 25) * 1000,
          color: alert.severity === 'Severe' ? '#ef4444' : '#f59e0b',
          fillColor: alert.severity === 'Severe' ? '#ef4444' : '#f59e0b',
          fillOpacity: 0.16,
          weight: 1.5,
          dashArray: '4, 4'
        });

        circle.bindPopup(`
          <div class="text-xs p-1.5 font-sans">
            <div class="font-extrabold text-amber-900">${alert.title}</div>
            <div class="text-[10px] font-bold text-amber-700">${alert.severity} Hazard Impact Zone</div>
            <p class="text-[11px] text-slate-600 mt-1">${alert.description}</p>
          </div>
        `);

        circle.addTo(group);
      }
    });
  }, [alerts]);

  // 4.5. Render K-Means Demand Zones (40 demand points + visually distinct cluster centres)
  useEffect(() => {
    if (!mapRef.current || !demandZonesLayerGroupRef.current) return;
    const group = demandZonesLayerGroupRef.current;
    group.clearLayers();

    if (!showDemandZones || !demandZones) return;

    // 1) Draw each assigned delivery-demand point coloured by its K-Means cluster_id
    demandZones.points.forEach((pt) => {
      const clusterColor = getClusterColor(pt.cluster_id);
      const radius = Math.max(5.5, Math.min(9.5, 4.5 + Math.sqrt(pt.demand_units) * 0.25));

      const pointMarker = L.circleMarker([pt.latitude, pt.longitude], {
        radius,
        color: '#ffffff',
        weight: 1.75,
        fillColor: clusterColor,
        fillOpacity: 0.88
      });

      pointMarker.bindTooltip(
        `<div class="p-1 text-xs font-sans">
          <strong style="color: ${clusterColor}">Demand Point #${pt.point_index + 1} (Zone #${pt.cluster_id})</strong><br/>
          Demand: <strong>${pt.demand_units} units</strong> · Priority: <span class="uppercase font-semibold">${pt.priority}</span><br/>
          <span class="text-[10px] text-amber-800 font-semibold">SYNTHETIC DEMO (${pt.data_source})</span>
        </div>`,
        { sticky: true }
      );

      pointMarker.bindPopup(
        `<div class="text-xs p-1.5 font-sans max-w-[230px]">
          <div class="font-extrabold text-slate-900" style="color: ${clusterColor}">
            Delivery Demand Point #${pt.point_index + 1}
          </div>
          <div class="text-[10px] font-bold uppercase mt-0.5 text-slate-600">
            Assigned Cluster: Zone #${pt.cluster_id}
          </div>
          <div class="mt-1 text-[11px] text-slate-700 space-y-0.5">
            <div>Demand Volume: <strong>${pt.demand_units} units</strong></div>
            <div>Priority Tier: <strong class="uppercase">${pt.priority}</strong></div>
            <div>Dist. to Centre: <strong>${pt.distance_to_cluster_center_m.toFixed(0)} m</strong></div>
            <div class="font-mono text-[10px] text-slate-500">
              ${pt.latitude.toFixed(4)}°N, ${pt.longitude.toFixed(4)}°E
            </div>
          </div>
          <div class="mt-1.5 px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-[9px] font-extrabold text-amber-900">
            DEMONSTRATION DATA — SYNTHETIC DEMAND (${pt.data_source})
          </div>
        </div>`
      );

      pointMarker.addTo(group);
    });

    // 2) Draw each K-Means cluster centre with a visually distinct hub marker & subtle radius ring
    demandZones.clusters.forEach((cluster) => {
      const clusterColor = getClusterColor(cluster.cluster_id);

      // Subtle dashed cohesion ring showing mean distance to cluster centre
      if (cluster.mean_distance_to_center_m > 0) {
        const ring = L.circle([cluster.center_lat, cluster.center_lng], {
          radius: cluster.mean_distance_to_center_m,
          color: clusterColor,
          fillColor: clusterColor,
          fillOpacity: 0.06,
          weight: 1.5,
          dashArray: '4, 5',
          interactive: false
        });
        ring.addTo(group);
      }

      const centerIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `
          <div class="relative flex items-center justify-center">
            <div class="w-7 h-7 rounded-lg text-white font-black text-[11px] shadow-lg border-2 border-white flex items-center justify-center ring-2 ring-slate-900/20 hover:scale-110 transition-transform" style="background-color: ${clusterColor};">
              ★${cluster.cluster_id}
            </div>
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      const centerMarker = L.marker([cluster.center_lat, cluster.center_lng], {
        icon: centerIcon,
        zIndexOffset: 600
      });

      centerMarker.bindTooltip(
        `<div class="p-1 text-xs font-sans">
          <strong style="color: ${clusterColor}">★ K-Means Cluster Centre #${cluster.cluster_id}</strong><br/>
          ${cluster.point_count} demand points · <strong>${cluster.total_demand_units.toFixed(0)} total units</strong> (${cluster.demand_share_pct.toFixed(1)}%)<br/>
          <span class="text-[10px] text-amber-800 font-semibold">DEMONSTRATION DATA — SYNTHETIC DEMAND</span>
        </div>`,
        { sticky: true }
      );

      centerMarker.bindPopup(
        `<div class="text-xs p-1.5 font-sans max-w-[240px]">
          <div class="font-extrabold text-sm" style="color: ${clusterColor}">
            ★ Cluster Zone #${cluster.cluster_id} Centre
          </div>
          <div class="text-[10px] font-bold uppercase text-slate-500 mt-0.5">
            K-Means Centroid (Projected UTM 46N → WGS84)
          </div>
          <div class="mt-1.5 text-[11px] text-slate-700 space-y-0.5">
            <div>Assigned Points: <strong>${cluster.point_count} locations</strong></div>
            <div>Total Demand: <strong>${cluster.total_demand_units.toFixed(0)} units</strong> (${cluster.demand_share_pct.toFixed(1)}% share)</div>
            <div>Mean Spread: <strong>${cluster.mean_distance_to_center_m.toFixed(0)} m</strong> (max ${cluster.max_distance_to_center_m.toFixed(0)} m)</div>
            <div class="font-mono text-[10px] text-slate-500">
              ${cluster.center_lat.toFixed(5)}°N, ${cluster.center_lng.toFixed(5)}°E
            </div>
          </div>
          <div class="mt-1.5 px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-[9px] font-extrabold text-amber-900">
            DEMONSTRATION DATA — SYNTHETIC DEMAND, NOT REAL-WORLD OBSERVATIONS.
          </div>
        </div>`
      );

      centerMarker.addTo(group);
    });
  }, [demandZones, showDemandZones]);

  // 4.6. Render Road Accessibility Corridors (Module D)
  useEffect(() => {
    if (!mapRef.current || !accessibilityLayerGroupRef.current) return;
    const group = accessibilityLayerGroupRef.current;
    group.clearLayers();

    if (!showAccessibilityOverlay || roadSegments.length === 0) return;

    roadSegments.forEach((seg) => {
      if (!seg.coordinates || seg.coordinates.length < 2) return;

      const isBlocked = seg.status === 'blocked';
      const isRestricted = seg.status === 'restricted';
      const color = isBlocked ? '#ef4444' : isRestricted ? '#f59e0b' : '#10b981';
      const weight = isBlocked ? 5.5 : isRestricted ? 4.5 : 3.5;
      const dashArray = isBlocked ? '8, 8' : isRestricted ? '6, 6' : undefined;

      const polyline = L.polyline(seg.coordinates, {
        color,
        weight,
        opacity: 0.85,
        dashArray,
      });

      polyline.bindTooltip(
        `<div class="p-1 text-xs font-sans">
          <strong style="color: ${color}">${seg.name}</strong><br/>
          Status: <strong class="uppercase">${seg.status}</strong> · ${seg.district}<br/>
          <span class="text-[10px] text-slate-500">${seg.restriction_details || 'Open corridor'}</span>
        </div>`,
        { sticky: true }
      );

      polyline.bindPopup(
        `<div class="text-xs p-1.5 font-sans max-w-[240px]">
          <div class="font-bold text-slate-900" style="color: ${color}">
            ${seg.name}
          </div>
          <div class="text-[10px] font-semibold uppercase text-slate-500 mt-0.5">
            ${seg.district} • Class: ${seg.road_class.toUpperCase()}
          </div>
          <div class="mt-1 text-[11px] text-slate-700">
            Status: <span class="font-bold uppercase" style="color: ${color}">${seg.status}</span>
          </div>
          ${
            seg.restriction_details
              ? `<div class="mt-1 p-1 rounded bg-slate-50 border border-slate-200 text-[10px] text-slate-600">
                  ${seg.restriction_details}
                </div>`
              : ''
          }
        </div>`
      );

      polyline.addTo(group);
    });
  }, [roadSegments, showAccessibilityOverlay]);

  // 4.7. Render Field Incidents (Module E)
  useEffect(() => {
    if (!mapRef.current || !incidentsLayerGroupRef.current) return;
    const group = incidentsLayerGroupRef.current;
    group.clearLayers();

    if (!showAccessibilityOverlay || fieldIncidents.length === 0) return;

    fieldIncidents.forEach((inc) => {
      const isPending = inc.status === 'pending';
      const isResolved = inc.status === 'resolved';
      const color = isResolved ? '#10b981' : isPending ? '#f59e0b' : '#ef4444';

      const icon = L.divIcon({
        className: 'custom-div-icon',
        html: `
          <div class="relative flex items-center justify-center">
            <div class="w-6 h-6 rounded-full text-white font-bold text-[10px] shadow-lg border-2 border-white flex items-center justify-center ring-2 hover:scale-125 transition-transform" style="background-color: ${color};">
              !
            </div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([inc.latitude, inc.longitude], { icon });

      marker.bindTooltip(
        `<div class="p-1 text-xs font-sans">
          <strong style="color: ${color}">${inc.title}</strong> (${inc.status.toUpperCase()})<br/>
          ${inc.location_name} • Severity: <strong class="uppercase">${inc.severity}</strong>
        </div>`,
        { sticky: true }
      );

      marker.bindPopup(
        `<div class="text-xs p-1.5 font-sans max-w-[240px]">
          <div class="font-bold text-slate-900" style="color: ${color}">
            ${inc.title}
          </div>
          <div class="text-[10px] font-semibold uppercase text-slate-500 mt-0.5">
            ${inc.location_name} (${inc.district})
          </div>
          <div class="mt-1 text-[11px] text-slate-700">
            Type: <strong>${inc.incident_type.replace('_', ' ')}</strong> · Severity: <strong class="uppercase">${inc.severity}</strong>
          </div>
          <div class="mt-0.5 text-[10px] text-slate-600">
            Status: <strong class="uppercase" style="color: ${color}">${inc.status}</strong>
          </div>
          <p class="mt-1 text-[10px] text-slate-600 bg-slate-50 rounded p-1 border border-slate-100">
            ${inc.description}
          </p>
          ${
            inc.photo_url
              ? `<div class="mt-1.5">
                  <img src="${inc.photo_url}" alt="Evidence" class="w-full h-24 rounded object-cover border border-slate-200" />
                </div>`
              : ''
          }
        </div>`
      );

      marker.addTo(group);
    });
  }, [fieldIncidents, showAccessibilityOverlay]);

  // 4.8. Render GPS Fleet Vehicles & Active Deliveries (Module F)
  useEffect(() => {
    if (!mapRef.current || !vehiclesLayerGroupRef.current) return;
    const group = vehiclesLayerGroupRef.current;
    group.clearLayers();

    if (!showVehiclesOverlay || vehicles.length === 0) return;

    vehicles.forEach((veh) => {
      if (veh.current_latitude === null || veh.current_longitude === null) return;

      const activeDel = deliveries.find(
        (d) => d.vehicle_id === veh.vehicle_id && d.status !== 'delivered'
      );
      const isDeviated = activeDel?.is_deviated;
      const statusColor = isDeviated ? '#ef4444' : activeDel ? '#0284c7' : '#10b981';

      const icon = L.divIcon({
        className: 'custom-div-icon',
        html: `
          <div class="relative flex items-center justify-center">
            <div class="w-8 h-8 rounded-xl text-white font-bold text-[10px] shadow-lg border-2 border-white flex flex-col items-center justify-center ring-2 hover:scale-125 transition-all" style="background-color: ${statusColor}; ring-color: ${statusColor};">
              <span class="text-[12px] leading-none" style="transform: rotate(${veh.current_bearing}deg);">➤</span>
              <span class="text-[8px] font-mono leading-none mt-0.5">${veh.current_speed_kph.toFixed(0)}k</span>
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([veh.current_latitude, veh.current_longitude], { icon });

      marker.bindTooltip(
        `<div class="p-1 text-xs font-sans">
          <strong style="color: ${statusColor}">${veh.name}</strong> (${veh.vehicle_id})<br/>
          Speed: <strong>${veh.current_speed_kph.toFixed(0)} km/h</strong> · Bearing: <strong>${veh.current_bearing.toFixed(0)}°</strong><br/>
          ${activeDel ? `Mission: <strong>${activeDel.title}</strong>` : 'Available Fleet Vehicle'}
        </div>`,
        { sticky: true }
      );

      marker.bindPopup(
        `<div class="text-xs p-1.5 font-sans max-w-[240px]">
          <div class="font-bold text-slate-900" style="color: ${statusColor}">
            ${veh.name}
          </div>
          <div class="text-[10px] font-mono text-slate-500 mt-0.5">
            ${veh.vehicle_id} • Type: ${veh.vehicle_type}
          </div>
          <div class="mt-1 text-[11px] text-slate-700 space-y-0.5">
            <div>Driver: <strong>${veh.assigned_driver_name}</strong></div>
            <div>Speed: <strong>${veh.current_speed_kph.toFixed(0)} km/h</strong> · Bearing: <strong>${veh.current_bearing.toFixed(0)}°</strong></div>
            <div>Mode: <span class="uppercase font-semibold text-[10px] text-slate-600">${veh.telemetry_mode}</span></div>
          </div>
          ${
            activeDel
              ? `<div class="mt-1.5 p-1.5 rounded-lg bg-sky-50 border border-sky-200 text-[10px] space-y-0.5">
                  <div class="font-bold text-sky-950">${activeDel.title}</div>
                  <div class="text-sky-800">Progress: <strong>${activeDel.progress_pct.toFixed(0)}%</strong></div>
                  ${isDeviated ? `<div class="text-rose-700 font-bold">⚠️ Route Deviation: ${activeDel.deviation_distance_m.toFixed(0)}m off corridor</div>` : ''}
                </div>`
              : ''
          }
          <div class="mt-1.5 px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-[9px] font-semibold text-amber-900">
            DEMO MODE — SIMULATED GPS TELEMETRY
          </div>
        </div>`
      );

      marker.addTo(group);
    });
  }, [vehicles, deliveries, showVehiclesOverlay]);

  // 5. Render RainViewer Radar Overlay Layer
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    if (radarTileLayerRef.current) {
      map.removeLayer(radarTileLayerRef.current);
      radarTileLayerRef.current = null;
    }

    if (radar.isActive && radar.frames.length > 0) {
      const currentFrame = radar.frames[radar.currentFrameIndex];
      if (currentFrame) {
        const tileUrl = getRadarTileUrl(radar.host, currentFrame.path);

        const layer = L.tileLayer(tileUrl, {
          opacity: 0.68,
          zIndex: 400,
          maxNativeZoom: 7,
          maxZoom: 19,
          className: 'radar-tile-layer'
        });

        layer.addTo(map);
        radarTileLayerRef.current = layer;
      }
    }
  }, [radar.isActive, radar.currentFrameIndex, radar.frames, radar.host]);

  return (
    <div className="relative w-full h-full bg-slate-100 overflow-hidden">
      <div ref={mapContainerRef} className="w-full h-full z-10" />

      {/* Minimal Top-Right Recenter & Region Scale Buttons */}
      <div className="absolute top-4 right-4 z-[1000] flex items-center gap-2">
        <button
          type="button"
          onClick={handleFocusNER}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/95 backdrop-blur-md border border-slate-200/90 text-slate-700 hover:text-slate-950 font-medium text-xs shadow-sm hover:shadow transition-all cursor-pointer"
        >
          <LocateFixed className="w-3.5 h-3.5 text-slate-500" />
          <span>Fit corridor</span>
        </button>
        <button
          type="button"
          onClick={handleFocusFullNER}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/95 backdrop-blur-md border border-slate-200/90 text-slate-700 hover:text-slate-950 font-medium text-xs shadow-sm hover:shadow transition-all cursor-pointer"
        >
          <Globe className="w-3.5 h-3.5 text-slate-500" />
          <span>8-State NER map</span>
        </button>
      </div>

      {/* Minimal Bottom-Left Legend Pill */}
      <div className="absolute bottom-4 left-4 z-[1000] pointer-events-none">
        <div className="px-3 py-1.5 rounded-xl bg-white/90 backdrop-blur-md border border-slate-200/80 shadow-xs flex items-center gap-3 text-[11px] font-medium text-slate-600">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-1 rounded-full bg-blue-600 inline-block" />
            Recommended
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-1 rounded-full bg-amber-500 inline-block" />
            Alternative
          </span>
          {showDemandZones && demandZones && (
            <span className="flex items-center gap-1.5 pl-2 border-l border-slate-200">
              <span className="w-2 h-2 rounded-full bg-purple-600 inline-block" />
              Demand Zones (K={demandZones.n_clusters})
            </span>
          )}
          {showAccessibilityOverlay && roadSegments.length > 0 && (
            <span className="flex items-center gap-1.5 pl-2 border-l border-slate-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
              Accessibility Corridors ({roadSegments.length})
            </span>
          )}
          {showVehiclesOverlay && vehicles.length > 0 && (
            <span className="flex items-center gap-1.5 pl-2 border-l border-slate-200">
              <span className="w-2 h-2 rounded-full bg-sky-500 inline-block" />
              GPS Fleet ({vehicles.length})
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
