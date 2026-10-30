# NER SmartRoute — Evaluation & Demonstration Guide (SIH 26002)

> **Step-by-step walkthrough script for examiners, evaluators, and judges reviewing SIH 26002: AI Logistics & Accessibility Intelligence.**

---

## Quick Navigation of Live Demo Scenarios

1. [Scenario 1: Intelligent Mountain Logistics Routing (Module A)](#scenario-1-intelligent-mountain-logistics-routing)
2. [Scenario 2: Route-Ranking Machine Learning Pipeline (Module B)](#scenario-2-route-ranking-machine-learning-pipeline)
3. [Scenario 3: Numerical Weather & Spatial Disruptions (Module C)](#scenario-3-numerical-weather--spatial-disruptions)
4. [Scenario 4: Road Accessibility & Geo-Tagged Field Incident Reporting (Module D & E)](#scenario-4-road-accessibility--field-reporting)
5. [Scenario 5: GPS Fleet Tracking & Deviation Engine (Module F)](#scenario-5-gps-fleet-tracking--deviation-engine)
6. [Scenario 6: Automated Multi-Hazard Alerts & Deduplication (Module G)](#scenario-6-automated-multi-hazard-alerts)
7. [Scenario 7: Multilingual (English / Hindi) & Offline PWA Sync Queue (Module H)](#scenario-7-multilingual--offline-sync-queue)

---

## Pre-Demo Checklist

1. **Verify Backend is running:**
   ```powershell
   # Health check returns status="ok", loaded_nodes=21764
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
   ```
2. **Verify Frontend is running:**
   * Open `http://127.0.0.1:5174/` (or `5173`) in any modern browser (Chrome, Edge, Firefox).

---

## Scenario 1: Intelligent Mountain Logistics Routing

**Objective:** Demonstrate terrain-aware, multi-criteria mountain routing that avoids the false assumptions of straight-line distance.

1. **Start Screen:** On the Welcome screen, note the clean GIS branding and click **Plan Logistics Corridor**.
2. **Endpoints Selection:**
   * Origin: **Shillong Hub** (`25.5788, 91.8933`)
   * Destination: **Sohra CHC** (`25.2750, 91.7323`)
   * Observe the green badge: `Routable in loaded graph (snap: 5.8 m)`.
   * Click **Continue**.
3. **Mission Details:**
   * Goods: `Medical Supplies`
   * Urgency: `Emergency`
   * Vehicle: `4×4`
   * Priority: `Balanced`
   * Click **Calculate route**.
4. **Interactive Map & Candidates:**
   * Observe the 3 distinct candidate routes rendered on Leaflet:
     * `estimated_fastest` (cyan): Primary mountain arterial corridor.
     * `shortest` (purple dashed): Shorter metric distance, but lower road hierarchy and longer duration.
     * `alternative_corridor` (amber dashed): Penalized bypass route.
   * Toggle between the 4 priority pills (`Balanced`, `Fastest`, `Shortest`, `Access`) and observe the dynamic re-ranking.

---

## Scenario 2: Route-Ranking Machine Learning Pipeline

**Objective:** Show the experimental Pairwise Logistic Regression ML ranker and its rigorous evaluation transparency.

1. In the side sheet, expand the drawer: **AI / ML Ranking (Experimental)**.
2. **Review Candidate Probabilities:**
   * The model evaluates feature difference vectors across 11 dimensions.
   * Observe predicted win probabilities for each candidate route.
3. **Review Evaluation Benchmark Table:**
   * Points out the 5 comparative methods:
     * `PairwiseRouteRanker (Ours)`
     * `Distance-only heuristic`
     * `Travel-time heuristic`
     * `Road hierarchy heuristic`
     * `Random baseline`
   * Highlight the **GroupShuffleSplit (60/20/20)** evaluation preventing data leakage across geographic queries.
4. **Academic Integrity Note:** Point out the disclosure stating that the ML model is evaluated for ranking intelligence, while the underlying routing path uses deterministic NetworkX Dijkstra on verified OSM geometries.

---

## Scenario 3: Numerical Weather & Spatial Disruptions

**Objective:** Demonstrate live meteorological hazard scoring and spatial polyline intersection with verified regional advisories.

1. In the route summary card, observe:
   * **Weather Hazard Score:** Real-time Open-Meteo precipitation and wind speed sampling along the route corridor (with guidance notes).
   * **Active Regional Advisory Check:** Corridor intersection with official advisories (e.g. Mawkdok Valley shoulder repair or Umiam Spillway bridge restriction).
2. Expand the **Score Breakdown** drawer to review individual components:
   * Distance Score ($S_{\text{dist}}$)
   * Time Score ($S_{\text{time}}$)
   * Road Hierarchy Score ($S_{\text{hier}}$)
   * Weather Exposure Score ($S_{\text{weather}}$)
   * Confirmed Disruptions Score ($S_{\text{disrupt}}$)
   * Snap Quality Score ($S_{\text{snap}}$)
   * Completeness Score ($S_{\text{comp}}$)
   * Note that `Live Traffic Score` is explicitly reported as `None` (no live traffic fabrication).

---

## Scenario 4: Road Accessibility & Field Reporting

**Objective:** Demonstrate citizen/driver geo-tagged incident reporting and the admin verification workflow.

1. **Submit Incident:**
   * In the top header, click the red **Report** button.
   * Fill out the incident modal:
     * Title: `Mawkdok Escarpment Rockfall`
     * Category: `Rockfall`
     * Severity: `Severe`
     * Reporter: `Driver Sangma (Field Logistics)`
     * Description: `Single-lane flow obstructed by loose boulders after morning rain.`
   * Click **Submit Report** (or **Save Offline Draft** if simulating disconnection).
   * Observe the status badge: `Status: PENDING REVIEW` (adheres to the rule that unverified reports do not auto-block highways).
2. **Review in Monitor Panel:**
   * Expand the **Corridors & Incidents** drawer.
   * Switch to the **Field Reports Queue** tab.
   * Click **Verify Report** on the newly submitted incident.
   * Switch to the **Immutable Audit Trail** tab and verify the logged timestamp, reviewer ID, and previous/new status.

---

## Scenario 5: GPS Fleet Tracking & Deviation Engine

**Objective:** Demonstrate real-time delivery dispatch, telemetry updates, and route corridor adherence detection.

1. **Dispatch Cargo:**
   * In the header, click the blue **Dispatch** button.
   * Note that the active route corridor, distance ($52.9\,\text{km}$), and duration are pre-filled.
   * Select vehicle `ML-05-AB-1001` (Mahindra Bolero 4x4) and click **Dispatch Delivery**.
2. **Monitor Telemetry:**
   * Expand the **GPS Fleet & Deliveries** drawer.
   * Click **Step GPS** to advance the vehicle coordinates along the verified OSM polyline.
   * Observe the interactive vehicle marker moving on the map with bearing rotation and speed indicators.
3. **Route Deviation Detection:**
   * Note that if telemetry reports a coordinate $>500\,\text{m}$ from the planned corridor, `is_deviated` flags true and triggers an emergency off-corridor notification.

---

## Scenario 6: Automated Multi-Hazard Alerts

**Objective:** Demonstrate the notification center with SHA-256 compound deduplication and cross-service polling.

1. In the header, click the **Alerts** bell (with unread badge counter).
2. Click **Sync Automated Triggers**:
   * Polls `AccessibilityService`, `DisruptionsService`, and `TrackingService` simultaneously.
   * Demonstrates SHA-256 deduplication hashing (`category:entity_id:date_bucket`) to ensure repeated checks never create duplicate spam.
3. Switch to the **Notification Channels** tab:
   * Shows the honesty disclosure: `in_app` is marked active/live, while `sms_adapter` and `push_webhook` are ready but unconfigured.

---

## Scenario 7: Multilingual & Offline Sync Queue

**Objective:** Demonstrate accessibility for non-English speakers and resilience in remote mountain cellular blackouts.

1. **Bilingual Localization:**
   * In the top-right header, click the language toggle button `[हिन्दी (HI)]`.
   * Observe the entire interface updating instantly into Hindi (स्थान चयन, कार्यक्षेत्र, अनुशंसित मार्ग, मौसम सुरक्षा स्कोर, सिंक कतार, etc.).
   * Click `[English (EN)]` to toggle back.
2. **Offline Draft Queue (PWA Capability):**
   * Click the **Sync** button in the header.
   * Displays the offline queue manager showing stored local drafts.
   * When connectivity drops or when users click **Save Offline Draft**, reports are persisted in `localStorage`.
   * As soon as network reconnects (`window.addEventListener('online')`), the system automatically drains the queue and posts the incident reports to the backend.
3. **Floating GIS Status Pill:**
   * Point out the live telemetry pill on the map showing connected OSM road nodes ($21,764$), active advisories, active fleet count, and network connection status.

---

## Summary of Completed Acceptance Criteria

* [x] **Preserved regression test suites:** All 9 backend test suites pass cleanly with exit code 0.
* [x] **Frontend build & lint:** `tsc -b && vite build` built in under 1 second; `oxlint` reports 0 errors.
* [x] **Academic integrity compliance:** All scientific disclosures, synthetic demand labels, and static speed notes are strictly enforced.
* [x] **Zero dangling background locks:** Backend and frontend run smoothly in host mode.

