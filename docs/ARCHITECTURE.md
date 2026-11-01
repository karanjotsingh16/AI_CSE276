# NER SmartRoute — Codebase Architecture & Directory Guide (SIH 26002)

> **Architectural overview of the organized codebase for developers, evaluators, and system auditors.**

---

## 1. Directory Organization

```
d:\AI and ML Project\
├── README.md                          # Master project documentation
├── AGENTS.md                          # Engineering memory & verified change log
├── docs/                              # Technical guides & documentation
│   ├── ARCHITECTURE.md                # This directory organization reference
│   └── EVALUATION_AND_DEMO_GUIDE.md   # Step-by-step 7-scenario demo walkthrough
│
├── backend/                           # FastAPI Backend Service (Python 3.12)
│   ├── main.py                        # FastAPI REST API application & endpoints
│   ├── run_all_tests.py               # Master regression test orchestrator
│   ├── requirements.txt               # Pinned Python package dependencies
│   ├── README.md                      # Backend service documentation
│   │
│   ├── core/                          # Routing algorithms, graph logic & ML
│   │   ├── __init__.py                # Package exports
│   │   ├── route_engine.py            # OSMnx/NetworkX Dijkstra pathfinding & alternative corridors
│   │   ├── route_scoring.py           # Multi-criteria explainable route scoring
│   │   ├── route_ranking_ml.py        # Pairwise Logistic Ranker & benchmarks
│   │   ├── region_manager.py          # 8-state NER catalog & LRU engine cache
│   │   ├── demand_clustering.py       # UTM 46N projected K-Means clustering
│   │   └── pan_india_routing.py       # Public OSRM routing client with fallback
│   │
│   ├── services/                      # Domain services & business logic
│   │   ├── __init__.py                # Package exports
│   │   ├── accessibility_service.py   # Road accessibility, seed corridors & incident audit logs
│   │   ├── alerts_service.py          # Multi-hazard alerts with SHA-256 deduplication
│   │   ├── tracking_service.py        # GPS vehicle tracking, dispatch & deviation engine
│   │   ├── weather_service.py         # Open-Meteo numerical weather integration & caching
│   │   ├── disruptions_service.py     # Verified regional advisories & spatial polyline checks
│   │   └── geocoding_service.py       # Multi-tier gazetteer & cached Nominatim geocoder
│   │
│   ├── scripts/                       # Graph ETL & maintenance tools
│   │   ├── __init__.py
│   │   ├── download_roads.py          # OSMnx road graph download script
│   │   └── preprocess_roads.py        # Graph cleaning & speed imputation script
│   │
│   ├── tests/                         # Automated unit & integration test suites
│   │   ├── __init__.py
│   │   ├── test_alerts_system.py
│   │   ├── test_vehicle_tracking.py
│   │   ├── test_accessibility_and_reports.py
│   │   ├── test_weather_and_disruptions.py
│   │   ├── test_route_scoring.py
│   │   ├── test_route_engine.py
│   │   ├── test_route_ranking_ml.py
│   │   ├── test_geocoding_and_regions.py
│   │   ├── test_demand_clustering.py
│   │   ├── test_api.py
│   │   └── test_demand_api.py
│   │
│   ├── data/                          # Data persistence & road graphs
│   │   ├── raw/                       # Raw OpenStreetMap graphs
│   │   ├── processed/                 # Cleaned GraphML road networks
│   │   ├── cache/                     # Disk caches (weather, geocode)
│   │   ├── uploads/                   # Geo-tagged field report incident photos
│   │   ├── accessibility.db           # SQLite database
│   │   ├── tracking.db                # SQLite database
│   │   ├── alerts.db                  # SQLite database
│   │   ├── regional_disruptions.json  # Verified advisories
│   │   ├── regions_catalog.json       # 10 catalog regions across 8 NER states
│   │   └── sample_delivery_demand.csv # Synthetic demonstration demand points
│   │
│   ├── models/                        # Serialized ML artifacts
│   │   └── pairwise_route_ranker_v1.joblib
│   │
│   └── reports/                       # Generated audit & evaluation JSON reports
│       ├── road_data_audit.json
│       ├── demand_clustering_evaluation.json
│       └── route_ranking_ml_evaluation.json
│
└── frontend/                          # Single Page Web App (React 19 + TypeScript)
    ├── package.json                   # Scripts & dependencies
    ├── vite.config.ts                 # Vite bundler configuration
    ├── index.html                     # HTML root, PWA manifest & SW links
    ├── public/                        # Static public assets
    │   ├── manifest.webmanifest       # Standalone PWA web manifest
    │   ├── sw.js                      # Offline caching service worker
    │   └── favicon.svg                # Application branding vector icon
    │
    └── src/
        ├── App.tsx                    # Minimalist 5-stage flow & workspace side sheet
        ├── main.tsx                   # React root & LanguageProvider
        ├── index.css                  # Global styles & Tailwind setup
        ├── App.css
        │
        ├── components/                # Modular React components
        │   ├── index.ts               # Central barrel exports
        │   ├── common/                # Shared header & search components
        │   │   ├── Header.tsx
        │   │   └── LocationSearchInput.tsx
        │   ├── map/                   # Interactive Leaflet GIS map
        │   │   ├── MapView.tsx
        │   │   ├── MapLegend.tsx
        │   │   └── RadarControl.tsx
        │   ├── modals/                # Modal dialogs
        │   │   ├── FieldReportModal.tsx
        │   │   ├── NewDeliveryModal.tsx
        │   │   ├── NotificationCenterModal.tsx
        │   │   └── OfflineQueueModal.tsx
        │   ├── panels/                # Workspace drawers
        │   │   ├── AccessibilityMonitorPanel.tsx
        │   │   ├── TrackingMonitorPanel.tsx
        │   │   └── DemandZonesCard.tsx
        │   └── legacy/                # Preserved domain assessment cards
        │       ├── CriticalInfrastructureCard.tsx
        │       ├── DisasterAlertsCard.tsx
        │       ├── DisasterNewsCard.tsx
        │       ├── LogisticsMissionCard.tsx
        │       ├── LogisticsRecommendationCard.tsx
        │       ├── RegionalIntelligenceCard.tsx
        │       ├── RouteAlternativesCard.tsx
        │       ├── RouteSafetyCard.tsx
        │       ├── TrustedDataSourcesCard.tsx
        │       └── WeatherIntelligenceCard.tsx
        │
        ├── services/                  # HTTP clients for backend APIs
        │   ├── accessibilityService.ts
        │   ├── alertService.ts
        │   ├── demandZoneService.ts
        │   ├── geocodingService.ts
        │   ├── notificationService.ts
        │   ├── offlineQueueService.ts
        │   ├── routeService.ts
        │   ├── trackingService.ts
        │   └── weatherService.ts
        │
        ├── logic/                     # Scoring formulas, formatters & risk evaluation
        │   ├── formatters.ts
        │   ├── routeRisk.ts
        │   ├── routeScoring.ts
        │   └── weatherRisk.ts
        │
        ├── types/                     # TypeScript type definitions
        │   ├── accessibility.ts
        │   ├── alert.ts
        │   ├── demandZone.ts
        │   ├── geocoding.ts
        │   ├── infrastructure.ts
        │   ├── mission.ts
        │   ├── news.ts
        │   ├── notification.ts
        │   ├── radar.ts
        │   ├── route.ts
        │   ├── sources.ts
        │   ├── tracking.ts
        │   └── weather.ts
        │
        ├── data/                      # Client-side presets & hub lists
        │   ├── demoScenarios.ts
        │   ├── facilities.ts
        │   ├── locations.ts
        │   └── sourcesRegistry.ts
        │
        ├── i18n/                      # English & Hindi (हिंदी) translations
        │   ├── translations.ts
        │   ├── context.ts
        │   ├── LanguageContext.tsx
        │   ├── useTranslation.ts
        │   └── index.ts
        │
        └── assets/                    # Image assets
            └── hero.png
```

---

## 2. Backward Compatibility Architecture

To guarantee that past commands, evaluation scripts, and existing import statements never break:
1. **Python Shims:** The top-level `backend/` directory maintains clean compatibility shims for all core modules, domain services, and test files. Any script running `from route_engine import RouteEngine` or executing `python test_route_engine.py` continues to work with zero errors.
2. **TypeScript Barrel Exports:** `frontend/src/components/index.ts` re-exports all components, and legacy path shims in `components/` ensure existing imports resolve without requiring global import refactors.
3. **Deterministic Paths:** All file path resolutions compute directory roots dynamically (`BACKEND_DIR`), ensuring data files in `backend/data/` and reports in `backend/reports/` are accurately located regardless of whether an import is initiated from `backend/` or `backend/core/` or `backend/services/`.
