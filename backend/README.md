# NER SmartRoute Backend (SIH 26002)

Backend routing engine, K-Means demand-zone clustering module, and FastAPI service for **SIH 26002 — AI Logistics & Accessibility Intelligence (NER SmartRoute)** covering the Shillong–Sohra region in Meghalaya.

## Directory Contents

- `data/raw/shillong_roads.graphml` — Raw OpenStreetMap road network (cleaned in-place).
- `data/processed/shillong_roads_clean.graphml` — Strongly connected road graph (`21,764` nodes, `53,888` directed edges) with pre-imputed mountain highway `speed_kph` and `travel_time` attributes.
- `data/sample_delivery_demand.csv` — 40 synthetic demonstration delivery-demand records (`data_source = "synthetic_demo"`).
- `reports/road_data_audit.json` — Graph audit report, bounding box, and node-snapping verification.
- `reports/demand_clustering_evaluation.json` — K-Means clustering evaluation report (`EPSG:32646` projection, cluster summaries, and internal metrics).
- `download_roads.py` — Downloads the 25 km bounding-box road graph around `(25.42, 91.82)`.
- `preprocess_roads.py` — Filters the graph to its largest strongly connected component and imputes mountain road speeds and travel times.
- `route_engine.py` — Standalone `RouteEngine` class (loads the GraphML once, enforces the `3,000 m` maximum snapping distance, and computes `shortest` and `estimated_fastest` routes).
- `demand_clustering.py` — Standalone `DemandZoneClusterer` class (projects `EPSG:4326` coordinates to `EPSG:32646` metres, fits K-Means, and computes cluster summaries and internal metrics).
- `main.py` — FastAPI application exposing `GET /health`, `POST /api/routes`, and `POST /api/demand-zones` with CORS restricted to `http://localhost:5173` and `http://127.0.0.1:5173`.
- `test_route_engine.py` — Automated test script for the standalone route engine.
- `test_demand_clustering.py` — Automated test script for the standalone K-Means demand clustering module.
- `test_api.py` — Automated test suite for `GET /health` and `POST /api/routes`.
- `test_demand_api.py` — Automated test suite for `POST /api/demand-zones`.

---

## Windows PowerShell Commands (Run inside `PS D:\AI and ML Project\backend>`)

### 1. Install Dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

### 2. Run Standalone Module Tests

```powershell
.\.venv\Scripts\python.exe .\test_demand_clustering.py
.\.venv\Scripts\python.exe .\test_route_engine.py
```

### 3. Run FastAPI Endpoint Tests (`TestClient`)

```powershell
.\.venv\Scripts\python.exe .\test_demand_api.py
.\.venv\Scripts\python.exe .\test_api.py
```

### 4. Start the FastAPI Server

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 5. Probe the Live Server in PowerShell

Check `GET /health`:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health" | ConvertTo-Json -Depth 5
```

Calculate demand zones (`POST /api/demand-zones`):

```powershell
$demandBody = @{ n_clusters = 4; random_state = 42 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/demand-zones" -ContentType "application/json" -Body $demandBody | ConvertTo-Json -Depth 5
```
