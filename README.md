# NER SmartRoute — AI Logistics & Accessibility Intelligence (SIH 26002)

> **Autonomous Terrain-Aware Logistics, Multi-Hazard Alerting, Fleet Tracking & Accessibility Intelligence for North-East India (Meghalaya Pilot)**  
> **Challenge:** Smart India Hackathon (SIH) 26002 — AI Logistics & Accessibility Intelligence  
> **Course / Track:** CSE276  
> **Pilot Geographic Focus:** Meghalaya (Shillong, Sohra, Mairang, Dawki) & 8-State North Eastern Region (NER)  
> **Interactive Visualizer:** [`docs/arch.html`](file:///d:/AI%20and%20ML%20Project/docs/arch.html) (Live animated system workflows & flowcharts)

---

## 1. Executive Summary & Problem Context

North-East India faces unique logistics, disaster vulnerability, and accessibility challenges:
* **Rugged Himalayan & Shillong Plateau Topography:** Winding mountain roads with steep grades, hairpin curves, and variable surface qualities where straight-line distance is fundamentally misleading.
* **Severe Weather & Natural Hazards:** Extreme monsoon precipitation, frequent landslides, rockfalls, fog visibility reductions, and flash floods routinely sever vital transportation arteries (e.g., NH-6, NH-10).
* **Intermittent Cellular Coverage:** Deep river gorges and mountain passes often have zero mobile signal, rendering cloud-only logistics apps inoperable for field crews and drivers.
* **Fragile Critical Infrastructure:** Single-lane bridges and spillway decks have strict axle weight restrictions, making real-time accessibility intelligence essential for emergency medical and relief transport.

**NER SmartRoute** addresses these challenges with an end-to-end GIS platform combining **deterministic graph algorithms**, **machine learning route ranking**, **numerical weather integration**, **field-verified road accessibility auditing**, **GPS fleet tracking**, **automated hazard alerts**, **offline-first PWA sync queues**, and **animated interactive architectural visualizers**.

---

## 2. System Architecture & Module Breakdown

```text
+----------------------------------------------------------------------------------------------------+
|                                    NER SmartRoute Architecture                                     |
+----------------------------------------------------------------------------------------------------+
                                                  │
          ┌───────────────────────────────────────┴───────────────────────────────────────┐
          ▼                                                                               ▼
┌──────────────────────────────────────────┐                         ┌──────────────────────────────────────────┐
│      FastAPI Backend Engine (Python)     │                         │        Frontend Web App (React 19)       │
├──────────────────────────────────────────┤                         ├──────────────────────────────────────────┤
│ • core/: Dijkstra, ML, K-Means, OSRM     │                         │ • Minimalist 5-Stage Mission Wizard      │
│ • services/: Accessibility, GPS, Alerts  │  HTTP / REST / JSON     │ • Interactive Leaflet Vector GIS Map     │
│ • scripts/: OSM Download & Preprocessing │ ◄─────────────────────► │ • Bilingual i18n Toggle (English / हिंदी)│
│ • tests/: 11 Automated Test Suites       │  CORS: localhost:5173/4 │ • PWA Service Worker & Offline Sync      │
│ • SQLite: accessibility, tracking, alerts│                         │ • Modular Drawers & Modal Dialogs        │
│ • 100% Backward Compatibility Shims      │                         │ • Component Directory Modularization     │
└──────────────────────────────────────────┘                         └──────────────────────────────────────────┘
                                                  │
                                                  ▼
                         ┌──────────────────────────────────────────────────┐
                         │   Interactive Animated Architecture Visualizer   │
                         │             (docs/arch.html)                     │
                         ├──────────────────────────────────────────────────┤
                         │ • 10-Stage Animated Pipeline Simulator           │
                         │ • 6 Dedicated Interactive Mermaid Flowcharts     │
                         │ • Deep-Dive Technical Component Inspector        │
                         │ • Explainable AI Preference Weight Simulator     │
                         └──────────────────────────────────────────────────┘
```

### Module Matrix

| Module | Purpose | Organized Subpackage & Implementation Files |
|---|---|---|
| **Module A** | **Intelligent Route Optimization** | `backend/core/` ([`route_engine.py`](file:///d:/AI%20and%20ML%20Project/backend/core/route_engine.py), [`route_scoring.py`](file:///d:/AI%20and%20ML%20Project/backend/core/route_scoring.py), [`region_manager.py`](file:///d:/AI%20and%20ML%20Project/backend/core/region_manager.py)) |
| **Module B** | **Route-Ranking Machine Learning** | `backend/core/` ([`route_ranking_ml.py`](file:///d:/AI%20and%20ML%20Project/backend/core/route_ranking_ml.py), [`demand_clustering.py`](file:///d:/AI%20and%20ML%20Project/backend/core/demand_clustering.py)) |
| **Module C** | **Weather Intelligence & Disruptions** | `backend/services/` ([`weather_service.py`](file:///d:/AI%20and%20ML%20Project/backend/services/weather_service.py), [`disruptions_service.py`](file:///d:/AI%20and%20ML%20Project/backend/services/disruptions_service.py)) |
| **Module D** | **Road Accessibility Monitoring** | `backend/services/` ([`accessibility_service.py`](file:///d:/AI%20and%20ML%20Project/backend/services/accessibility_service.py), `data/accessibility.db`) |
| **Module E** | **Field Incident Reporting & Workflow** | `frontend/src/components/modals/` ([`FieldReportModal.tsx`](file:///d:/AI%20and%20ML%20Project/frontend/src/components/modals/FieldReportModal.tsx), `panels/` [`AccessibilityMonitorPanel.tsx`](file:///d:/AI%20and%20ML%20Project/frontend/src/components/panels/AccessibilityMonitorPanel.tsx)) |
| **Module F** | **GPS Vehicle & Delivery Tracking** | `backend/services/` ([`tracking_service.py`](file:///d:/AI%20and%20ML%20Project/backend/services/tracking_service.py), `data/tracking.db`, `panels/` [`TrackingMonitorPanel.tsx`](file:///d:/AI%20and%20ML%20Project/frontend/src/components/panels/TrackingMonitorPanel.tsx)) |
| **Module G** | **Automated Alerts & Notifications** | `backend/services/` ([`alerts_service.py`](file:///d:/AI%20and%20ML%20Project/backend/services/alerts_service.py), `data/alerts.db`, `modals/` [`NotificationCenterModal.tsx`](file:///d:/AI%20and%20ML%20Project/frontend/src/components/modals/NotificationCenterModal.tsx)) |
| **Module H** | **Multilingual i18n, PWA & Offline Sync** | `frontend/src/i18n/`, `services/` ([`offlineQueueService.ts`](file:///d:/AI%20and%20ML%20Project/frontend/src/services/offlineQueueService.ts), `modals/` [`OfflineQueueModal.tsx`](file:///d:/AI%20and%20ML%20Project/frontend/src/components/modals/OfflineQueueModal.tsx)) |
| **Interactive Docs** | **Animated System Architecture Visualizer** | `docs/` ([`arch.html`](file:///d:/AI%20and%20ML%20Project/docs/arch.html), [`index.html`](file:///d:/AI%20and%20ML%20Project/docs/index.html), [`ARCHITECTURE.md`](file:///d:/AI%20and%20ML%20Project/docs/ARCHITECTURE.md)) |

---

## 3. Academic Integrity & Scientific Disclosures

To uphold scientific integrity and academic guidelines (CSE276 / SIH 26002):

1. **Deterministic Routing vs. Machine Learning:**
   * Primary route pathfinding is computed deterministically via **NetworkX Dijkstra** on OpenStreetMap road graphs (`shillong_roads_clean.graphml`, 21,764 nodes, 53,888 edges).
   * The **PairwiseRouteRanker** is an experimental evaluation model trained on 11-dimension differential feature vectors ($\Delta x = x_A - x_B$) using scikit-learn Logistic Regression and evaluated with query-grouped splits (`GroupShuffleSplit` 60/20/20 grouped by origin-destination OD-pair). It does not alter verified graph geometries.
2. **Static Travel Times (No Live Traffic Fabrication):**
   * Travel durations are static estimates derived from OSM highway classification speed imputation (`trunk`: 50 km/h, `primary`: 40 km/h, `secondary`: 30 km/h, `tertiary`: 25 km/h, `unclassified`: 20 km/h).
   * Live traffic scoring is strictly disabled and transparently marked as `None` / unavailable.
3. **Synthetic Demonstration Demand Data:**
   * Delivery demand data in `sample_delivery_demand.csv` is synthetic demonstration data.
   * Silhouette ($0.868$) and Davies-Bouldin ($0.182$) scores are internal unsupervised geometric cohesion metrics on projected metric coordinates (`EPSG:32646`), not predictive accuracy.
4. **Demonstration GPS Telemetry:**
   * Fleet vehicle simulation advances along genuine OpenStreetMap node coordinates and is clearly badged as `DEMONSTRATION MODE`.
5. **Channel Adapter Registry:**
   * External notification adapters (`sms_adapter`, `email_adapter`, `push_webhook`) are documented as ready but unconfigured; only the verified `in_app` notification delivery is reported as active.

---

## 4. Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4, Leaflet GIS, Lucide React, Oxlint |
| **Backend** | Python 3.12, FastAPI, Uvicorn, OSMnx, NetworkX, Scikit-learn, Scipy, NumPy, HTTPX, Pydantic v2 |
| **Databases** | SQLite (`accessibility.db`, `tracking.db`, `alerts.db`), OpenStreetMap GraphML |
| **APIs Integrated** | Open-Meteo WMO 0.25° Numerical Weather Model, Nominatim Geocoder (rate-limited & disk-cached) |
| **PWA & Offline** | Web App Manifest, Service Worker (`sw.js`), LocalStorage persistent incident draft queue |
| **Documentation & Visualizer** | Interactive HTML5 Visualizer (`docs/arch.html`), Mermaid 11, KaTeX mathematical typography |

---

## 5. Quickstart & Verification Guide

### Prerequisites
* Windows PowerShell (or Linux/macOS bash)
* Python 3.12 (with virtual environment in `backend/.venv`)
* Node.js v18+ & npm

### Step 1: Start the FastAPI Backend
```powershell
Set-Location "d:\AI and ML Project\backend"
& ".\.venv\Scripts\uvicorn.exe" main:app --host 127.0.0.1 --port 8000 --reload
```
* **Interactive API Documentation (Swagger):** `http://127.0.0.1:8000/docs`
* **Health Check Endpoint:** `http://127.0.0.1:8000/health`

### Step 2: Start the Frontend Application
```powershell
Set-Location "d:\AI and ML Project\frontend"
npm install
npm run dev -- --host 127.0.0.1
```
* **Application URL:** `http://127.0.0.1:5174/` (or `5173`)

### Step 3: Run Full Backend Regression Tests
```powershell
Set-Location "d:\AI and ML Project\backend"
.\.venv\Scripts\python.exe run_all_tests.py
```
*(All 9 test suites execute and pass 100% in ~48s).*

Or run individual test suites from `backend/tests/` or via top-level shims:
```powershell
.\.venv\Scripts\python.exe tests/test_alerts_system.py
.\.venv\Scripts\python.exe tests/test_vehicle_tracking.py
.\.venv\Scripts\python.exe tests/test_accessibility_and_reports.py
.\.venv\Scripts\python.exe tests/test_weather_and_disruptions.py
.\.venv\Scripts\python.exe tests/test_route_scoring.py
.\.venv\Scripts\python.exe tests/test_route_engine.py
.\.venv\Scripts\python.exe tests/test_route_ranking_ml.py
.\.venv\Scripts\python.exe tests/test_geocoding_and_regions.py
.\.venv\Scripts\python.exe tests/test_demand_clustering.py
```

### Step 4: Frontend Build & Lint Verification
```powershell
Set-Location "d:\AI and ML Project\frontend"
npm run build   # Type-checks and builds production bundle (built in ~750ms)
npm run lint    # Runs oxlint with 0 errors
```

### Step 5: View the Interactive Architecture Visualizer
Open [`docs/arch.html`](file:///d:/AI%20and%20ML%20Project/docs/arch.html) directly in any web browser, or serve it locally:
```powershell
python -m http.server 8080 --directory "d:\AI and ML Project\docs"
# Open http://localhost:8080/arch.html in your browser
```

---

## 6. Key REST API Endpoints

### Routing & Geocoding
* `POST /api/routes`: Computes candidate routes (`shortest`, `estimated_fastest`, `alternative_corridor`), snaps coordinates (max 3,000m), and attaches multi-criteria scores, weather hazard scores, and regional disruption intersections.
* `POST /api/geocode`: Resolves text queries or coordinate strings with 8-state gazetteer lookup, Nominatim fallback, and coverage metadata.
* `GET /api/regions`: Returns catalog of 10 regions across all 8 NER states with lazy LRU graph manager.

### Machine Learning & Demand Zones
* `GET /api/ml-ranking/evaluation`: Reports 5-model benchmark evaluation, learned logistic weights, and group shuffle split accuracy.
* `POST /api/demand-zones`: Projects coordinates to UTM Zone 46N (`EPSG:32646`), fits K-Means ($K=2..6$), and returns cluster centroids, demand shares, and cohesion metrics.

### Road Accessibility & Field Reports
* `GET /api/accessibility/segments`: Monitored road corridors with structural clearance and accessibility grades.
* `GET /api/accessibility/incidents`: Query field incident reports by status (`pending`, `verified`, `resolved`, `rejected`) and hazard type.
* `POST /api/accessibility/reports`: Submit new field incident report (starts as `pending`).
* `PATCH /api/accessibility/incidents/{id}/status`: Authorised admin workflow to verify or reject incident reports, logging to `accessibility_audit_log`.
* `POST /api/accessibility/upload-photo`: Validated multipart photo upload with 5 MB file size limit.

### GPS Vehicle & Delivery Tracking
* `GET /api/tracking/vehicles`: Fleet inventory with vehicle type, capacity, assigned driver, and live coordinates.
* `GET /api/tracking/deliveries`: Active logistics missions with destination, goods, and progress.
* `POST /api/tracking/deliveries`: Dispatch cargo along calculated route corridor with static ETA.
* `POST /api/tracking/deliveries/{id}/simulate-step`: Advances demonstration GPS step along planned route.
* `POST /api/tracking/telemetry`: Records telemetry and detects off-corridor deviations ($>500\,\text{m}$).

### Multi-Hazard Alerts & Notifications
* `GET /api/notifications`: Retrieves alerts filtered by unread status, severity, and category.
* `GET /api/notifications/unread-count`: Lightweight badge counter for workspace header.
* `PATCH /api/notifications/{id}/read`: Toggle individual notification read state.
* `POST /api/notifications/sync-triggers`: Automated evaluation of cross-service triggers with compound SHA-256 deduplication.
* `GET /api/notifications/channels`: Channel adapter registry with delivery transparency.

---

## 7. Project File Structure

```text
d:\AI and ML Project\
├── AGENTS.md                                # Shared engineering context, rules & changelog
├── README.md                                # Master project documentation (UTF-8)
│
├── docs/                                    # System architecture & evaluation guides
│   ├── arch.html                            # Interactive animated architecture & workflow visualizer
│   ├── index.html                           # Web mirror of interactive visualizer
│   ├── ARCHITECTURE.md                      # Comprehensive modular architecture blueprint
│   └── EVALUATION_AND_DEMO_GUIDE.md         # Evaluator walkthrough script (7 live scenarios)
│
├── backend/
│   ├── core/                                # Graph pathfinding, multi-criteria scoring & ML
│   │   ├── route_engine.py                  # OSMnx NetworkX Dijkstra & snapping engine
│   │   ├── route_scoring.py                 # Multi-criteria explainable scoring (4 preferences)
│   │   ├── route_ranking_ml.py              # Pairwise Logistic Ranker & benchmarks
│   │   ├── region_manager.py                # 8-state NER catalog & LRU graph manager
│   │   ├── demand_clustering.py             # K-Means projected UTM 46N demand clustering
│   │   ├── pan_india_routing.py             # Pan-India OSRM corridor fallback routing
│   │   └── __init__.py
│   │
│   ├── services/                            # Operational domain services (SQLite & external APIs)
│   │   ├── accessibility_service.py         # SQLite road accessibility, incident queue & audit trail
│   │   ├── tracking_service.py              # SQLite fleet registry, delivery dispatch & 500m deviation
│   │   ├── alerts_service.py                # Multi-hazard alerts with SHA-256 compound deduplication
│   │   ├── weather_service.py               # Open-Meteo numerical weather with 15-min cache
│   │   ├── disruptions_service.py           # Spatial polyline disruption detection
│   │   ├── geocoding_service.py             # Multi-tier gazetteer & cached Nominatim geocoder
│   │   └── __init__.py
│   │
│   ├── scripts/                             # Offline data pipeline
│   │   ├── download_roads.py                # OSMnx road graph acquisition
│   │   ├── preprocess_roads.py              # Graph cleaning & mountain speed imputation
│   │   └── __init__.py
│   │
│   ├── tests/                               # 11 Standalone automated test suites
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
│   │   ├── test_demand_api.py
│   │   └── __init__.py
│   │
│   ├── data/                                # Spatial data, databases & artifacts
│   │   ├── processed/shillong_roads_clean.graphml # 21,764 nodes / 53,888 edges
│   │   ├── regions_catalog.json             # 10 catalog regions across 8 NER states
│   │   ├── regional_disruptions.json        # Verified mountain highway advisories
│   │   ├── sample_delivery_demand.csv       # Labeled synthetic demand dataset
│   │   ├── accessibility.db                 # SQLite: road corridors, reports, audit logs
│   │   ├── tracking.db                      # SQLite: vehicles, deliveries, telemetry logs
│   │   ├── alerts.db                        # SQLite: multi-hazard alerts & dispatches
│   │   └── uploads/                         # Validated citizen photo uploads (≤ 5MB)
│   │
│   ├── models/
│   │   └── pairwise_route_ranker_v1.joblib  # Serialized ML model artifact
│   │
│   ├── reports/                             # Evaluation JSON reports
│   │   ├── road_data_audit.json
│   │   ├── demand_clustering_evaluation.json
│   │   └── route_ranking_ml_evaluation.json
│   │
│   ├── main.py                              # FastAPI REST application & routers
│   ├── run_all_tests.py                     # Master test suite runner
│   ├── requirements.txt                     # Verified dependency manifest
│   ├── README.md                            # Backend documentation
│   └── *.py (shims)                         # 100% backward-compatible root re-exports
│
└── frontend/
    ├── public/
    │   ├── manifest.webmanifest             # Standalone PWA manifest
    │   ├── sw.js                            # Offline caching service worker
    │   └── favicon.svg                      # App logo mark
    │
    ├── src/
    │   ├── App.tsx                          # 5-stage UI flow & GIS workspace
    │   ├── i18n/                            # English & Hindi (हिंदी) bilingual translation
    │   │   ├── en.ts
    │   │   ├── hi.ts
    │   │   └── index.tsx
    │   │
    │   ├── components/
    │   │   ├── modals/                      # Modal dialogs
    │   │   │   ├── FieldReportModal.tsx     # Incident reporting with offline draft option
    │   │   │   ├── NewDeliveryModal.tsx     # Cargo dispatch & vehicle assignment
    │   │   │   ├── NotificationCenterModal.tsx # Multi-hazard alerts dialog
    │   │   │   └── OfflineQueueModal.tsx    # Persistent offline sync queue manager
    │   │   │
    │   │   ├── panels/                      # Drawers & monitoring panels
    │   │   │   ├── AccessibilityMonitorPanel.tsx # Corridors, reports & audit log
    │   │   │   ├── TrackingMonitorPanel.tsx # Fleet status & GPS stepping player
    │   │   │   └── DemandZonesCard.tsx      # K-Means demand zones breakdown
    │   │   │
    │   │   ├── map/                         # GIS mapping layers & controls
    │   │   │   ├── MapView.tsx              # Interactive Leaflet map with corridors
    │   │   │   ├── MapLegend.tsx            # Visual symbology legend
    │   │   │   └── RadarControl.tsx         # RainViewer radar animation controller
    │   │   │
    │   │   ├── common/                      # Navigation & inputs
    │   │   │   ├── Header.tsx               # Top navbar & language toggle
    │   │   │   └── LocationSearchInput.tsx  # Autocomplete search & quick-pick pills
    │   │   │
    │   │   ├── legacy/                      # 10 preserved reference cards
    │   │   ├── index.ts                     # Barrel export for all components
    │   │   └── *.tsx (shims)                # Re-export compatibility shims
    │   │
    │   ├── services/                        # API client services
    │   │   ├── routeService.ts
    │   │   ├── accessibilityService.ts
    │   │   ├── trackingService.ts
    │   │   ├── notificationService.ts
    │   │   ├── offlineQueueService.ts
    │   │   └── geocodingService.ts
    │   │
    │   ├── logic/                           # Client-side scoring & formatters
    │   ├── types/                           # TypeScript data interfaces
    │   └── data/locations.ts                # Verified coordinates for 8 NER states
    │
    ├── package.json
    ├── vite.config.ts
    └── README.md                            # Frontend documentation
```

---

## 8. Verification & Test Certification

All **9 test suites** and frontend production checks pass cleanly with exit code `0`:

* Master Regression Runner: `python run_all_tests.py` — **100% REGRESSION PASS (48.39s)**
* `test_alerts_system.py`: `Ran 6 tests in 0.41s — OK`
* `test_vehicle_tracking.py`: `Ran 7 tests in 0.43s — OK`
* `test_accessibility_and_reports.py`: `Ran 7 tests in 0.40s — OK`
* `test_weather_and_disruptions.py`: `Ran 5 test phases — ALL PASSED (8.60s)`
* `test_route_scoring.py`: `Ran 5 test phases across 4 preferences — ALL PASSED (14.42s)`
* `test_route_engine.py`: `Ran 7 test phases — ALL PASSED (10.31s)`
* `test_route_ranking_ml.py`: `Ran 7 test phases — ALL PASSED (4.28s)`
* `test_geocoding_and_regions.py`: `Ran 6 test phases — ALL PASSED (6.39s)`
* `test_demand_clustering.py`: `Ran 6 test phases — ALL PASSED (3.14s)`
* `frontend tsc -b && vite build`: `built in 748ms — exit code 0`
* `frontend oxlint`: `88 files checked — 0 errors`

---

## 9. License & Attribution

* **Course & Hackathon:** CSE276 — Smart India Hackathon (SIH) 26002
* **Road Network Data:** © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL).
* **Atmospheric Forecast Data:** [Open-Meteo Numerical Weather API](https://open-meteo.com/) (CC BY 4.0 / WMO).
* **Regional Disruption Advisories:** Synthesized from official notices by NHIDCL, BRO, Meghalaya SDMA, and MeECL.
