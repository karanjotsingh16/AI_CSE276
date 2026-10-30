# AGENTS.md — Shared Context & Change Log for AI Agents

> **Every agent (any model) working in this repository MUST:**
> 1. Read this whole file before making changes.
> 2. After ANY change to code, data, config, or running services, append an entry to the
>    **Change Log** (newest at the top) and update **Current State / In-Progress Work** if affected.
> 3. Never delete past log entries. Correct mistakes by adding a new entry.
> 4. Keep entries short, factual, and tied to file paths. Record what was verified (commands + exit codes)
>    and what was NOT verified.

---

## 1. Project Overview

- **Course / Challenge:** CSE276 — SIH 26002 "AI Logistics & Accessibility Intelligence"
- **Product name:** NER SmartRoute (logistics route planning for North-East India, Meghalaya pilot)
- **Root:** `D:\AI and ML Project`
- **Academic integrity rules (non-negotiable):**
  - Never fabricate data, metrics, model accuracy, live traffic, or risk predictions.
  - Clearly separate the **graph-based routing algorithm** (NetworkX shortest path) from any **trained ML model**.
  - The demand dataset is **synthetic** — always label it
    `DEMONSTRATION DATA — SYNTHETIC DEMAND, NOT REAL-WORLD OBSERVATIONS.`
  - Silhouette / Davies–Bouldin are **internal clustering metrics**, not predictive accuracy, and must never be used as route scores.
  - Travel times are **static estimates** from road-class speed imputation, not live traffic.

## 2. Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, Leaflet, lucide-react, oxlint |
| Backend | Python, FastAPI, Uvicorn, OSMnx, NetworkX, scikit-learn, httpx |
| Data | OSM GraphML road graph, synthetic demand CSV |

## 3. How to Run / Verify

```powershell
# Backend (venv lives INSIDE backend/, not the repo root)
& "d:\AI and ML Project\backend\.venv\Scripts\uvicorn.exe" main:app --app-dir "d:\AI and ML Project\backend" --host 127.0.0.1 --port 8000 --reload --reload-dir "d:\AI and ML Project\backend"
# Health: http://127.0.0.1:8000/health   Docs: http://127.0.0.1:8000/docs

# Frontend (dev server on http://localhost:5173)
Set-Location "d:\AI and ML Project\frontend"; npm run dev
Set-Location "d:\AI and ML Project\frontend"; npm run build; npm run lint

# Backend tests (standalone scripts, run from backend/)
Set-Location "d:\AI and ML Project\backend"
.\.venv\Scripts\python.exe test_route_engine.py
.\.venv\Scripts\python.exe test_route_scoring.py
.\.venv\Scripts\python.exe test_geocoding_and_regions.py
.\.venv\Scripts\python.exe test_route_ranking_ml.py
.\.venv\Scripts\python.exe test_demand_clustering.py
.\.venv\Scripts\python.exe test_api.py          # uses TestClient; has hung in sandbox before
.\.venv\Scripts\python.exe test_demand_api.py   # uses TestClient; has hung in sandbox before
```

**Gotchas**
- A **stale Uvicorn process on port 8000** once caused `body -> preference: Extra inputs are not permitted`
  (old schema with `extra="forbid"`). Check with `netstat -ano | Select-String ":8000"` and kill old PIDs before assuming a code bug.
- CORS only allows `http://localhost:5173` and `http://127.0.0.1:5173`.
- Lint has ~13 pre-existing **warnings** (unused vars in legacy components); 0 errors is the bar.

## 4. Architecture

### Backend (`backend/`)
| File | Purpose |
|---|---|
| `main.py` | FastAPI app, Pydantic schemas, exception handlers, endpoints |
| `route_engine.py` | `RouteEngine`: loads `data/processed/shillong_roads_clean.graphml` once, snaps coordinates (max 3,000 m), computes `shortest` (length) and `estimated_fastest` (travel_time) |
| `route_scoring.py` | Deterministic component scores (distance, time, road hierarchy, snap quality) + weighted overall score per preference |
| `route_ranking_ml.py` | Experimental `PairwiseRouteRanker` (GroupShuffleSplit eval); report in `reports/route_ranking_ml_evaluation.json` |
| `region_manager.py` | Regional graph catalog (`data/regions_catalog.json`), coverage evaluation, LRU engine cache, `--acquire` CLI |
| `geocoding_service.py` | Local gazetteer + coordinate parser + rate-limited, disk-cached Nominatim; attaches coverage info |
| `pan_india_routing.py` | **NEW (in progress)**: India-wide routing via public OSRM, with offline fallback |
| `demand_clustering.py` | K-Means on synthetic demand (UTM 46N projection); report in `reports/demand_clustering_evaluation.json` |
| `download_roads.py`, `preprocess_roads.py` | Graph acquisition and cleaning |

**Endpoints:** `GET /health`, `POST /api/routes`, `POST /api/demand-zones`, `GET/POST /api/geocode`,
`GET /api/geocode/suggestions`, `GET /api/regions`, `GET /api/ml-ranking/evaluation`.

**Local graph facts:** 21,764 nodes / 53,888 directed edges; bounds lat 25.195–25.645, lng 91.572–92.069.
Covered hubs: Shillong, Police Bazar, Laitumkhrah, Upper Shillong, Smit, Mawphlang, Sohra, Mairang, Pynursla, Dawki.
NOT covered by the local graph: Guwahati, Jowai, Nongpoh.

### Frontend (`frontend/src/`)
- `App.tsx`: minimalist 5-stage flow: `welcome → endpoints → details → calculating → workspace`.
  The workspace shows the map plus a 400 px side sheet (priority switcher, route summary, route list, and collapsible
  "Score breakdown" and "Demand zones (K-Means)" drawers).
- `components/MapView.tsx`: Leaflet map; routes, origin/destination markers, and demand overlay are independent layer groups.
- `components/LocationSearchInput.tsx`: search row + quick-pick pills.
- `services/routeService.ts`: calls `POST /api/routes` (currently sends origin + destination only), then ranks on the client.
- `logic/routeScoring.ts`: client-side deterministic scoring / ranking (`evaluateAndRankRoutes`, `PREFERENCE_CONFIGS`).
- `logic/formatters.ts`: formatting helpers, including `formatDurationHoursMinutes`.
- Legacy cards (`Disaster*`, `Weather*`, `RadarControl`, `RouteSafetyCard`, …) are mostly unused by the new UI. Do not delete them without asking.

## 5. Current State (keep updated)

- **Master Development Plan Progress:**
  - **Phase 0 (Codebase Audit & Gap Analysis):** Completed & approved by user (2026-10-30).
  - **Phase 1 (Routing Foundation — Module A):** Completed & verified (2026-10-30).
  - **Phase 2 (Route-Ranking ML — Priority B / Module B):** Completed & verified (2026-10-30).
- Backend server: running on `127.0.0.1:8000`; `/health` OK, `/api/ml-ranking/evaluation` OK, `/api/routes` OK.
- Frontend build + lint: passed 2026-10-30 (`tsc -b && vite build` exit code 0; `oxlint` 0 errors, 13 legacy warnings).
- Backend tests confirmed passing (2026-10-30, exit code 0):
  - `test_route_ranking_ml.py`
  - `test_route_engine.py`
  - `test_route_scoring.py`
  - `test_geocoding_and_regions.py`
  - `test_demand_clustering.py`

## 6. In-Progress Work (unfinished — read before continuing)

- **Completed Phase 2 (Route-Ranking ML & Evaluation Transparency):**
  - Expanded `PairwiseRouteRanker` ([`backend/route_ranking_ml.py`](file:///d:/AI%20and%20ML%20Project/backend/route_ranking_ml.py)) to 11-dimensional feature vectors (`pref_accessibility_x_hierarchy_penalty`), supporting all 4 preferences (`shortest`, `fastest`, `balanced`, `accessibility`).
  - Saved model artifact ([`backend/models/pairwise_route_ranker_v1.joblib`](file:///d:/AI%20and%20ML%20Project/backend/models/pairwise_route_ranker_v1.joblib)) with fast disk caching via `load_or_train()`.
  - Comprehensive 5-method benchmark comparison on held-out test set (288 pairs) across 240 queries with strict GroupShuffleSplit spatial partitioning: Pairwise ML Ranker (98.6% acc, 0.9997 NDCG@3) vs. Deterministic Multi-Criteria Baseline (88.2% acc, 0.9802 NDCG@3) vs. Single-Objective Heuristics.
  - Transparent frontend drawer in [`frontend/src/App.tsx`](file:///d:/AI%20and%20ML%20Project/frontend/src/App.tsx) displaying candidate win probabilities, benchmark comparison table, and clear academic integrity disclosures (synthetic benchmark vs. deterministic primary dispatch).
- **Next Phase:** Phase 3 — Weather Intelligence & Disruptions Integration.

## 7. Change Log (newest first)

### 2026-10-30 (Phase 2 — Route-Ranking ML Pipeline & Evaluation Transparency)
- `backend/route_ranking_ml.py`:
  - Upgraded feature representation to 11 dimensions with accessibility preference support.
  - Implemented `save_model_artifact` saving `backend/models/pairwise_route_ranker_v1.joblib` and `load_or_train()` fast-loading method.
  - Expanded benchmark evaluation to 5 methods including `road_hierarchy_heuristic`.
  - Added feature values and evaluation summary reporting to `rank_live_evaluation_candidates`.
- `backend/route_engine.py`: updated `get_cached_ml_ranker` to use `PairwiseRouteRanker.load_or_train(random_state=42)`.
- `backend/test_route_ranking_ml.py`: expanded tests to verify 240 benchmark queries across 4 preferences, model artifact saving/loading, and live candidate ranking.
- `frontend/src/types/route.ts`: expanded `BackendMlRankingInfo` with `feature_values_by_route` and `evaluation_metrics_summary`.
- `frontend/src/App.tsx`: added 3rd progressive disclosure drawer ("Route-ranking AI / ML (Experimental)") displaying candidate win probabilities, benchmark comparison table, and academic integrity disclaimers.
- **Verified (all exit code 0):** `test_route_ranking_ml.py`, `test_route_engine.py`, `test_route_scoring.py`, `test_geocoding_and_regions.py`, `test_demand_clustering.py`, `npm run build`, `npm run lint` (0 errors), live `POST /api/routes` with `accessibility` preference.

### 2026-10-30 (Phase 1 — Module A: Intelligent Route Optimization)
- `backend/data/regions_catalog.json`: expanded regional road-graph catalog to 10 regions covering all 8 North Eastern states (Meghalaya, Assam, Arunachal Pradesh, Manipur, Mizoram, Nagaland, Tripura, Sikkim).
- `backend/geocoding_service.py`: added verified gazetteer entries across all 8 NER states (`gangtok_sikkim`, `rangpo_sikkim`, `dimapur_nagaland`, `naharlagun_arunachal`, `thoubal_manipur`, `lunglei_mizoram`, `udaipur_tripura`) and updated default suggestions.
- `backend/pan_india_routing.py`: removed synthetic curved-line fallback (`_build_offline_india_corridor`); now raises `OutOfCoverageError` when outside loaded graphs and OSRM is unreachable.
- `backend/route_engine.py` & `backend/main.py`: added `_compute_penalized_alternative_route` (`alternative_corridor`), `deduplicate_candidate_routes`, `data_provenance`, and `estimation_limitations`.
- `backend/route_scoring.py`: added `"accessibility"` preference (`0.25 * S_distance + 0.35 * S_time + 0.40 * S_hierarchy`), `completeness_score`, and `unavailable_component_scores`.
- `frontend/src/types/geocoding.ts`, `frontend/src/types/route.ts`, `frontend/src/logic/routeScoring.ts`, `frontend/src/services/routeService.ts`, `frontend/src/components/LocationSearchInput.tsx`, `frontend/src/components/MapView.tsx`, `frontend/src/App.tsx`: added 4th priority (`accessibility`), 3rd alternative corridor support, `X hr Y min` duration formatting everywhere, 8-state NER map view toggle, unavailable metrics disclosure, and `--acquire` CLI guidance.
- `backend/test_geocoding_and_regions.py` & `backend/test_route_scoring.py`: expanded tests for 8-state NER catalog, 4 preferences, 3rd distinct route alternative, and deduplication.
- **Verified (all exit code 0):** `test_geocoding_and_regions.py`, `test_route_scoring.py`, `test_route_engine.py`, `test_demand_clustering.py`, `npm run build`, `npm run lint` (0 errors).

### 2026-10-30 (earlier)
- **Created `AGENTS.md`** (this file) as shared memory for agents across model changes.
- Started FastAPI server (`--reload-dir backend`); `/health` → ok, graph loaded, `load_count=1`.
- Pan-India groundwork (see §6): added `backend/pan_india_routing.py`; edited `main.py` (scope field, service cache),
  `region_manager.py` (`within_india_network`), and `geocoding_service.py` (14 national cities, new featured list);
  rewrote `frontend/src/logic/formatters.ts` (added `splitDurationHoursMinutes`, `formatDurationHoursMinutes`;
  `formatDuration` now outputs `X hr Y min (est.)`). Verified: `python -c "import main"` OK. Not yet verified: India routing, frontend build.

### 2026-10-29 (late)
- Fixed the "Invalid Origin or Destination Coordinates / preference: Extra inputs are not permitted" error. Root cause:
  stale v0.2.0 Uvicorn process on port 8000. Killed it and restarted v0.3.0.
- `frontend/src/services/routeService.ts`: removed `preference` from the POST body (ranking is done on the client).
- `frontend/src/data/locations.ts`: replaced the out-of-coverage presets (Guwahati, Jowai, Nongpoh) with 10 covered hubs.
- `frontend/src/services/geocodingService.ts`: expanded `IN_COVERAGE_IDS`.
- `frontend/src/components/LocationSearchInput.tsx`: pills show only routable hubs.
- `frontend/src/App.tsx`: blocks Continue for same or out-of-coverage endpoints; added "Retry calculation" on route errors.
- `backend/main.py`: `/api/demand-zones` uses `isinstance(payload, DemandZonesRequest)` (direct-call fix).
- Verified: Dawki→Mairang `POST /api/routes` 200 (87.83 km fastest); frontend build/lint 0 errors; geocoding + scoring tests pass.

### 2026-10-29
- Minimalist UI rewrite: `App.tsx` (5-stage flow), `LocationSearchInput.tsx`, `MapView.tsx` (removed radar/legend clutter,
  added Reset view + legend pill), `index.css` (cubic-bezier animations). Build/lint passed.

### Earlier (summary)
- Backend core intelligence upgrade: `route_scoring.py`, `region_manager.py`, `regions_catalog.json`,
  `geocoding_service.py`, `route_ranking_ml.py` + report, enriched `/api/routes`, and new geocode/regions/ml-ranking endpoints.
- K-Means demand-zone integration and verification (`demand_clustering.py`, `/api/demand-zones`, `DemandZonesCard.tsx`).
- Fixed geocoder normalization to strip `[,;/()]` so "Shillong, Meghalaya" matches.

