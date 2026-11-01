# NER SmartRoute Backend (SIH 26002)

Backend routing engine, multi-criteria route scoring, pairwise ranking ML pipeline, GPS fleet tracking, road accessibility auditing, automated multi-hazard alerts, and FastAPI REST services for **SIH 26002 — AI Logistics & Accessibility Intelligence (NER SmartRoute)** covering Meghalaya and the 8 North-Eastern states of India.

---

## 1. Directory Structure

The backend is modularized into dedicated domain packages while providing top-level compatibility shims:

```text
backend/
├── core/                           # Routing algorithms & scientific ML models
│   ├── route_engine.py             # Dijkstra pathfinding & candidate route extraction
│   ├── route_scoring.py            # Multi-criteria explainable route scoring
│   ├── route_ranking_ml.py         # Pairwise Logistic Regression route ranker
│   ├── region_manager.py           # 8-state NER catalog & LRU graph manager
│   ├── demand_clustering.py        # K-Means demand clustering (EPSG:32646)
│   ├── pan_india_routing.py        # OSRM corridor fallback routing
│   └── __init__.py
│
├── services/                       # Application domain & operational services
│   ├── accessibility_service.py    # SQLite road accessibility & field reports
│   ├── tracking_service.py         # SQLite GPS fleet & delivery tracking
│   ├── alerts_service.py           # Multi-hazard alerts with SHA-256 deduplication
│   ├── weather_service.py          # Open-Meteo numerical weather integration
│   ├── disruptions_service.py      # Spatial polyline disruption detection
│   ├── geocoding_service.py        # 8-state gazetteer & rate-limited Nominatim
│   └── __init__.py
│
├── scripts/                        # Data acquisition & offline preprocessing
│   ├── download_roads.py           # OSMnx bounding box road graph acquisition
│   ├── preprocess_roads.py         # Graph cleaning & mountain speed imputation
│   └── __init__.py
│
├── tests/                          # Automated unit and integration test suites
│   ├── test_alerts_system.py
│   ├── test_vehicle_tracking.py
│   ├── test_accessibility_and_reports.py
│   ├── test_weather_and_disruptions.py
│   ├── test_route_scoring.py
│   ├── test_route_engine.py
│   ├── test_route_ranking_ml.py
│   ├── test_geocoding_and_regions.py
│   ├── test_demand_clustering.py
│   ├── test_api.py
│   ├── test_demand_api.py
│   └── __init__.py
│
├── data/                           # Geographic graphs, SQLite databases & synthetic demo data
│   ├── raw/                        # Raw downloaded road graphs
│   ├── processed/                  # Cleaned GraphML files (shillong_roads_clean.graphml)
│   ├── accessibility.db            # SQLite table for corridors, reports, audit log
│   ├── tracking.db                 # SQLite table for vehicles, deliveries, telemetry
│   ├── alerts.db                   # SQLite table for alerts & delivery status
│   ├── regions_catalog.json        # 8-state NER catalog
│   ├── regional_disruptions.json   # Verified mountain highway advisories
│   └── sample_delivery_demand.csv  # Labeled synthetic demand dataset
│
├── models/                         # Serialized ML model artifacts
│   └── pairwise_route_ranker_v1.joblib
│
├── reports/                        # Machine-readable audit and evaluation reports
│   ├── road_data_audit.json
│   ├── demand_clustering_evaluation.json
│   └── route_ranking_ml_evaluation.json
│
├── main.py                         # FastAPI REST application & endpoint routers
├── run_all_tests.py                # Single-command runner for all 9 test suites
├── requirements.txt                # Verified Python dependency specifications
└── *.py (shims)                    # Backward compatibility shims for root imports
```

---

## 2. Core Modules & Responsibilities

| Subpackage | File | Description |
|---|---|---|
| `core/` | `route_engine.py` | Loads GraphML once, snaps coordinates (max 3,000m), computes shortest (length) and estimated fastest (travel_time) routes. |
| `core/` | `route_scoring.py` | Multi-criteria scoring across 4 preferences (`balanced`, `distance`, `time`, `accessibility`). |
| `core/` | `route_ranking_ml.py` | Pairwise Logistic Ranker (11 feature differences, GroupShuffleSplit 60/20/20). |
| `core/` | `region_manager.py` | Catalog of 10 regions across 8 NER states; lazy LRU graph loading and on-demand acquisition. |
| `core/` | `demand_clustering.py` | K-Means clustering projected onto UTM 46N (EPSG:32646) for logistics zone planning. |
| `core/` | `pan_india_routing.py` | Pan-India fallback routing via public OSRM with bounding box safety checks. |
| `services/` | `accessibility_service.py` | Road corridor accessibility ratings, geo-tagged citizen incident reports, photo uploads, audit trail. |
| `services/` | `tracking_service.py` | Fleet vehicle registry, delivery dispatch, >500m corridor deviation detection, simulated GPS stepping. |
| `services/` | `alerts_service.py` | Compound SHA-256 deduplicated notification center with cross-service synchronization. |
| `services/` | `weather_service.py` | Live Open-Meteo numerical weather forecasts with 15-minute in-memory caching. |
| `services/` | `disruptions_service.py` | Regional mountain advisories with spatial polyline intersection evaluation. |
| `services/` | `geocoding_service.py` | Local gazetteer across 8 NER states + coordinate parser + cached Nominatim fallback. |

---

## 3. How to Run

### Install Dependencies
```powershell
Set-Location "d:\AI and ML Project\backend"
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

### Run All 9 Test Suites
```powershell
Set-Location "d:\AI and ML Project\backend"
.\.venv\Scripts\python.exe run_all_tests.py
```

### Run Individual Test Suites
```powershell
Set-Location "d:\AI and ML Project\backend"
.\.venv\Scripts\python.exe tests/test_route_engine.py
.\.venv\Scripts\python.exe tests/test_route_ranking_ml.py
.\.venv\Scripts\python.exe tests/test_alerts_system.py
.\.venv\Scripts\python.exe tests/test_vehicle_tracking.py
.\.venv\Scripts\python.exe tests/test_accessibility_and_reports.py
.\.venv\Scripts\python.exe tests/test_weather_and_disruptions.py
.\.venv\Scripts\python.exe tests/test_geocoding_and_regions.py
.\.venv\Scripts\python.exe tests/test_demand_clustering.py
```
*(Top-level shims e.g. `.\.venv\Scripts\python.exe test_route_engine.py` also work for full backward compatibility).*

### Start the FastAPI Server
```powershell
& "d:\AI and ML Project\backend\.venv\Scripts\uvicorn.exe" main:app --app-dir "d:\AI and ML Project\backend" --host 127.0.0.1 --port 8000 --reload --reload-dir "d:\AI and ML Project\backend"
```

### Health Check & API Docs
- **Health Endpoint:** `http://127.0.0.1:8000/health`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

## 4. Academic Integrity & Scientific Disclosures

1. **Routing:** All road pathfinding is computed using NetworkX Dijkstra shortest-path algorithms over OpenStreetMap GraphML data.
2. **Speed Imputation:** Travel durations are static estimates calculated via road-class design speeds (e.g., primary highway: 50 km/h; mountain unclassified: 20 km/h), not real-time traffic probe telemetry.
3. **Synthetic Demand:** The demand dataset is strictly labeled:
   `DEMONSTRATION DATA — SYNTHETIC DEMAND, NOT REAL-WORLD OBSERVATIONS.`
4. **Clustering Metrics:** Silhouette Coefficient and Davies–Bouldin Index are internal cluster separation metrics, never predictive accuracy scores.
5. **Experimental ML Ranker:** The pairwise ML ranker is an experimental decision-support model trained with GroupShuffleSplit cross-validation; it does not replace graph routing.
