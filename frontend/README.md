# SIH 26002 — AI Logistics & Accessibility Intelligence
### Government Alerts + Weather + OpenStreetMap + Risk-Aware Logistics (North Eastern Region)

A GIS-based logistics intelligence dashboard built for the North Eastern Region (Meghalaya Pilot Corridor) that compares delivery routes, displays real-time weather and precipitation radar, estimates multi-factor corridor risks, visualizes critical infrastructure, and recommends an optimal delivery route based on active terrain and atmospheric conditions.

---

## 1. System Architecture & Visual Design

The application is structured as a **single-screen, highly focused GIS logistics dashboard**:
- **Fixed Dark Navy Header** (`#101827`, 84px): Displays project branding, shield icon, subtitle, and the teal `NORTH EASTERN REGION` pilot corridor pill.
- **Left Independent Scrollable Panel** (~440px wide): Contains 10 feature cards stacked vertically with independent scrolling (`overflow-y: auto`), subtle borders, rounded corners, and clear metric values.
- **Right Interactive Map Workspace** (Full remaining viewport): Leaflet-powered GIS map featuring OpenStreetMap base tiles, route alternatives, custom SVG origin/destination markers, critical facilities, RainViewer radar overlay, floating `📍 Focus NER` button, floating `🌧️ LIVE PRECIPITATION RADAR` control panel, and a collapsible `MAP LEGEND`.

---

## 2. Feature Implementation & Data Provenance

| Feature Card | Integration Source | Current Operational Status | Notes / Limitations |
|---|---|---|---|
| **📦 Logistics Mission** | Client GIS Engine | **Live Operational** | Selectable goods, priority, quantity (kg), vehicle type, and NER pilot locations (Shillong, Sohra, Guwahati, Jowai, etc.). |
| **📊 Regional Intelligence** | Multi-factor Synthesis | **Live Synchronized** | 4 metric tiles: Active Alerts, Route Risk (0–100), Weather Risk (0–100), and Accessibility (0–100). |
| **🧠 AI Logistics Recommendation** | Multi-attribute Utility Engine | **Live Modelled** | 6-factor composite scoring with natural-language rationale generated from route metrics. |
| **🛣️ Route Alternatives** | OSRM + High-Res NER Highway Corridors | **Live & Deterministic Fallback** | Evaluates Route A (NH 206 Direct), Route B (SH-5 Highland Bypass), and Route C (Eastern Ridge). Clicking cards updates map highlights and all dashboard metrics. |
| **🌧️ Weather Intelligence** | Open-Meteo Forecast API (`api.open-meteo.com`) | **Live Connected** | Real-time precipitation probability, wind speed, temperature, and 6-hour forecast timeline. Never outputs fake 0% on failure. |
| **🚨 Disaster Alerts** | NDMA / SACHET CAP Portal (`sachet.ndma.gov.in`) | **Verified Regional CAP Notices** | Direct client-side fetch is subject to browser CORS. Uses verified CAP warning notices for Meghalaya (IMD/SDMA) with route intersection testing. Direct stream ready for FastAPI backend proxy. |
| **🧠 Route Safety** | Multi-source Synthesis | **Live Modelled** | Risk score, classification (`LOW`, `MODERATE`, `HIGH`, `UNAVAILABLE`), active alerts breakdown, and documented data limitations. |
| **🧠 AI Disaster News Intelligence** | Regional Publisher Registry | **Verified Regional Intelligence** | Real articles from *The Shillong Times*, *Northeast Now*, and *EastMojo* with links and timestamps. Structured for FastAPI news summarization. |
| **🏥 Critical Infrastructure** | OpenStreetMap & SDMA Registry | **Live Mapped** | Mapped hospitals/clinics, relief shelters, and logistics depots with category filter toggles and interactive map popups. |
| **🔎 Trusted Data Sources** | Multi-agency Provenance Registry | **Live & Documented** | Clickable links and operational status badges for NDMA, Open-Meteo, RainViewer, Copernicus DEM, GSI, FSI, and INCOIS. |
| **🌧️ Live Precipitation Radar** | RainViewer API (`api.rainviewer.com`) | **Live Connected** | Observed radar reflectivity tile overlay on the main map with play/pause multi-frame animation cycling and timestamp tracking. |

---

## 3. Logistics Scoring & Risk Model

The composite Logistics Score ($0-100$) uses transparent, configurable weights:
$$\text{LogisticsScore} = 0.30 \times T + 0.15 \times D + 0.20 \times A + 0.15 \times (100 - R_{\text{disaster}}) + 0.10 \times (100 - R_{\text{weather}}) + 0.10 \times (100 - R_{\text{terrain}})$$

Where:
- $T$: Travel-time efficiency normalized against candidate routes
- $D$: Distance efficiency normalized against candidate routes
- $A$: Accessibility / demand-reachability index ($0-100$)
- $R_{\text{disaster}}$: Modelled disaster exposure score ($0-100$)
- $R_{\text{weather}}$: Open-Meteo atmospheric risk score ($0-100$)
- $R_{\text{terrain}}$: Copernicus DEM slope gradient difficulty ($0-100$)

*Notice: Modelled estimates do not constitute official emergency instructions or certified road safety determinations.*

---

## 4. Technology Stack

- **Framework**: React 19 + TypeScript
- **Bundler**: Vite 8
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`) + Custom CSS utilities
- **Mapping**: Leaflet 1.9 + OpenStreetMap Tile Layer
- **Icons**: Lucide React
- **Radar**: RainViewer Weather Maps API

---

## 5. Local Setup & Running Commands

### Prerequisites
- Node.js (v18+)
- npm (v9+)

### Installation
```bash
# Clone or navigate to the project directory
cd "d:/AI and ML Project"

# Install dependencies
npm install
```

### Development Dev Server
```bash
# Start Vite development server
npm run dev
# The application will be accessible at http://localhost:5173/
```

### Production Build
```bash
# Run TypeScript verification and Vite production build
npm run build

# Preview production build locally
npm run preview
```

---

## 6. Python FastAPI AI Backend Integration Architecture

The service layer (`src/services/`) is modularized so that future Python FastAPI endpoints can replace client-side mock/proxy adapters seamlessly:
- **Routes & Scoring**: Replace `src/services/routeService.ts` calls with `POST /api/v1/routes/optimize`.
- **SACHET CAP Proxy**: Connect `src/services/alertService.ts` to `GET /api/v1/alerts/sachet-cap` to bypass browser CORS constraints.
- **News Extraction & NLP**: Connect `src/services/newsService.ts` to `GET /api/v1/intelligence/disaster-news`.
