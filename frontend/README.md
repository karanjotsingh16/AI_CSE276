# NER SmartRoute Frontend (SIH 26002)

Modern React 19 + TypeScript GIS web client for **SIH 26002 — AI Logistics & Accessibility Intelligence (NER SmartRoute)**. Features interactive Leaflet mapping, explainable multi-criteria routing, live Open-Meteo weather hazard overlays, road accessibility incident reporting, GPS delivery fleet tracking, notification center, offline draft sync queue, and English/Hindi (हिंदी) bilingual support.

---

## 1. Directory Structure

The frontend components and services are organized into clean domain-specific modules:

```text
frontend/src/
├── components/
│   ├── modals/                     # Modal dialogs & interactive user actions
│   │   ├── FieldReportModal.tsx    # Citizen & driver road incident reporting
│   │   ├── NewDeliveryModal.tsx    # Dispatch new delivery order with vehicle selection
│   │   ├── NotificationCenterModal.tsx # Multi-hazard alerts & delivery status modal
│   │   └── OfflineQueueModal.tsx   # Offline incident drafts sync manager
│   │
│   ├── panels/                     # Slide-over drawers & collapsible telemetry panels
│   │   ├── AccessibilityMonitorPanel.tsx # Corridors, field reports queue, audit trail
│   │   ├── TrackingMonitorPanel.tsx      # Fleet status, delivery progress, simulated GPS
│   │   └── DemandZonesCard.tsx           # K-Means demand cluster breakdown
│   │
│   ├── map/                        # GIS mapping & geospatial layers
│   │   ├── MapView.tsx             # Interactive Leaflet map (corridors, vehicles, alerts)
│   │   ├── MapLegend.tsx           # Visual symbology legend
│   │   └── RadarControl.tsx        # RainViewer precipitation radar animation
│   │
│   ├── common/                     # Core navigation & input controls
│   │   ├── Header.tsx              # Top navigation bar, branding, language toggle
│   │   └── LocationSearchInput.tsx # Autocomplete location search & quick-pick pills
│   │
│   ├── legacy/                     # Preserved reference & evaluation cards
│   │   ├── CriticalInfrastructureCard.tsx
│   │   ├── DisasterAlertsCard.tsx
│   │   ├── DisasterNewsCard.tsx
│   │   ├── LogisticsMissionCard.tsx
│   │   ├── LogisticsRecommendationCard.tsx
│   │   ├── RegionalIntelligenceCard.tsx
│   │   ├── RouteAlternativesCard.tsx
│   │   ├── RouteSafetyCard.tsx
│   │   ├── TrustedDataSourcesCard.tsx
│   │   └── WeatherIntelligenceCard.tsx
│   │
│   ├── index.ts                    # Barrel export for all components
│   └── *.tsx (shims)               # Backward compatibility shims for direct imports
│
├── services/                       # API communication & offline sync
│   ├── routeService.ts             # Calls backend /api/routes
│   ├── accessibilityService.ts     # Corridors, reports, photo uploads
│   ├── trackingService.ts          # Vehicle registry, deliveries, simulated GPS
│   ├── notificationService.ts      # Multi-hazard alerts & channel delivery status
│   ├── geocodingService.ts         # Gazetteer & Nominatim geocoding
│   ├── offlineQueueService.ts      # LocalStorage offline draft sync engine
│   ├── alertService.ts             # Regional disruptions & advisories
│   └── radarService.ts             # RainViewer precipitation radar frames
│
├── logic/                          # Client-side scoring, formatting & utilities
│   ├── routeScoring.ts             # Client-side 4-preference route evaluation
│   ├── formatters.ts               # Duration, distance, and timestamp formatting
│   └── routeRisk.ts                # Safety classification & hazard scoring
│
├── types/                          # TypeScript interface contracts
│   ├── route.ts
│   ├── accessibility.ts
│   ├── tracking.ts
│   ├── notification.ts
│   ├── geocoding.ts
│   ├── demandZone.ts
│   └── ...
│
├── i18n/                           # Bilingual localization (English & Hindi)
│   ├── en.ts                       # English translation dictionary
│   ├── hi.ts                       # Hindi (हिंदी) translation dictionary
│   └── index.tsx                   # React Context provider & useTranslation hook
│
├── data/                           # Geographic presets & pilot boundaries
│   └── locations.ts                # Verified coordinates for 8 NER states
│
├── App.tsx                         # 5-stage progressive disclosure workflow
└── main.tsx                        # React application bootstrap
```

---

## 2. Five-Stage Progressive Workflow

The user interface follows a focused 5-stage progressive disclosure flow:
1. **Welcome (`welcome`)**: Hero overview, SIH challenge statement, and quickstart CTA.
2. **Endpoints (`endpoints`)**: Origin and destination selector with 8-state NER gazetteer search and quick-pick pills.
3. **Details (`details`)**: Priority selector (`balanced`, `distance`, `time`, `accessibility`) and cargo specifications.
4. **Calculating (`calculating`)**: Loading animation displaying active OSM graph snapping and Dijkstra calculation.
5. **Workspace (`workspace`)**: Full-screen GIS workspace with:
   - Interactive Leaflet map (origin/destination markers, 3 alternative route corridors, real-time GPS vehicles, road incidents).
   - Side sheet with route summary, candidate corridor picker, and 5 collapsible disclosure drawers:
     1. **Score Breakdown Drawer**: Component score breakdown and formulas.
     2. **K-Means Demand Zones Drawer**: Spatial cluster summaries and internal separation metrics.
     3. **Route-Ranking AI/ML Drawer**: Pairwise win probabilities and 5-model benchmark comparison table.
     4. **Road Accessibility & Field Reports Drawer**: Corridor accessibility grades, pending incident verification, and audit log.
     5. **Fleet & Delivery Tracking Drawer**: Active vehicles, dispatch modal, >500m corridor deviation alerts, and simulated GPS step player.
   - Top Header with English / Hindi language toggle, notification center modal with unread badge, and offline sync queue status.

---

## 3. Development Commands

Run inside `PS D:\AI and ML Project\frontend>`:

```powershell
# Install npm dependencies
npm install

# Start development server (http://localhost:5173 or 5174)
npm run dev

# Run TypeScript type check and production build
npm run build

# Run Oxlint linter
npm run lint
```
