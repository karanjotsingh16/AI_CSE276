from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from functools import lru_cache
import math
import os
from typing import Any, Literal

from fastapi import Body, Depends, FastAPI, File, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from accessibility_service import AccessibilityService, UPLOADS_DIR
from tracking_service import TrackingService
from alerts_service import AlertsService
from demand_clustering import (
    DEFAULT_SAMPLE_DEMAND_CSV,
    DemandClusteringError,
    DemandZoneClusterer,
    EmptyDemandDatasetError,
    InsufficientDemandPointsError,
    InvalidClusterConfigurationError,
    InvalidDemandRecordError,
    load_demand_records_from_csv,
)
from geocoding_service import (
    EmptyGeocodeQueryError,
    GeocodingError,
    GeocodingService,
    InvalidCoordinateQueryError,
)
from pan_india_routing import PanIndiaRoutingService
from region_manager import RegionGraphManager
from route_engine import (
    DEFAULT_PROCESSED_GRAPH_PATH,
    GraphFileNotFoundError,
    InvalidCoordinateError,
    MAX_SNAP_DISTANCE_M,
    OutOfCoverageError,
    RouteEngine,
    RouteEngineError,
    UnreachableDestinationError,
    get_cached_ml_ranker,
    get_cached_weather_service,
    get_cached_disruptions_service,
)
from route_scoring import RoutePreferenceType

VITE_DEV_ORIGIN = "http://localhost:5173"
VITE_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"


@lru_cache(maxsize=1)
def get_cached_route_engine() -> RouteEngine:
    """Create and cache a single RouteEngine instance so the road graph loads only once."""
    return RouteEngine(
        graph_path=DEFAULT_PROCESSED_GRAPH_PATH,
        max_snap_distance_m=MAX_SNAP_DISTANCE_M,
    )


@lru_cache(maxsize=1)
def get_cached_region_manager() -> RegionGraphManager:
    """Create and cache the RegionGraphManager."""
    mgr = RegionGraphManager()
    try:
        engine = get_cached_route_engine()
        mgr.register_engine_instance(mgr.default_region_id, engine)
    except Exception:
        pass
    return mgr


@lru_cache(maxsize=1)
def get_cached_geocoding_service() -> GeocodingService:
    """Create and cache the GeocodingService."""
    return GeocodingService(
        region_manager=get_cached_region_manager(),
        allow_external_nominatim=True,
    )


@lru_cache(maxsize=1)
def get_cached_pan_india_service() -> PanIndiaRoutingService:
    """Create and cache the PanIndiaRoutingService."""
    return PanIndiaRoutingService()


@lru_cache(maxsize=1)
def get_cached_sample_demand_records() -> list[dict[str, Any]]:
    """Load and cache the synthetic demonstration demand dataset from CSV."""
    return load_demand_records_from_csv(DEFAULT_SAMPLE_DEMAND_CSV)


@lru_cache(maxsize=1)
def get_cached_accessibility_service() -> AccessibilityService:
    """Create and cache the AccessibilityService instance."""
    return AccessibilityService()


@lru_cache(maxsize=1)
def get_cached_tracking_service() -> TrackingService:
    """Create and cache the TrackingService instance."""
    return TrackingService()


@lru_cache(maxsize=1)
def get_cached_alerts_service() -> AlertsService:
    """Create and cache the AlertsService instance."""
    return AlertsService()


def get_route_engine(request: Request) -> RouteEngine:
    """FastAPI dependency returning the startup-initialized or cached RouteEngine instance."""
    engine = getattr(request.app.state, "route_engine", None)
    if engine is not None:
        return engine
    startup_error = getattr(request.app.state, "startup_error", None)
    if startup_error is not None:
        raise startup_error
    engine = get_cached_route_engine()
    request.app.state.route_engine = engine
    return engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application state; RouteEngine is cached on first health/route access."""
    if not hasattr(app.state, "route_engine"):
        app.state.route_engine = None
    if not hasattr(app.state, "startup_error"):
        app.state.startup_error = None
    yield


app = FastAPI(
    title="NER SmartRoute API — SIH 26002",
    description=(
        "AI Logistics & Accessibility Intelligence road-network routing, "
        "explainable multi-criteria route evaluation, geocoding, regional graph management, "
        "and K-Means demand-zone clustering API."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

# Restrict CORS to local development origins with regex fallback for alternate ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=VITE_ALLOWED_ORIGINS,
    allow_origin_regex=LOCAL_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def _check_finite_coord(val: Any, field_name: str, min_v: float, max_v: float) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"{field_name} must be a numeric float or int, got {type(val).__name__}.")
    num = float(val)
    if not math.isfinite(num):
        raise ValueError(f"{field_name} must be a finite number (not NaN or infinity).")
    if num < min_v or num > max_v:
        raise ValueError(f"{field_name} ({num}) must be between {min_v} and {max_v}.")
    return num


def _check_strict_int(val: Any, field_name: str) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError(f"{field_name} must be an integer, got {type(val).__name__}.")
    return int(val)


class CoordinatePoint(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)

    lat: float = Field(..., description="Latitude in decimal degrees [-90, 90]")
    lng: float = Field(..., description="Longitude in decimal degrees [-180, 180]")

    @field_validator("lat", mode="before")
    @classmethod
    def validate_lat(cls, v: Any) -> float:
        return _check_finite_coord(v, "latitude", -90.0, 90.0)

    @field_validator("lng", mode="before")
    @classmethod
    def validate_lng(cls, v: Any) -> float:
        return _check_finite_coord(v, "longitude", -180.0, 180.0)


class RouteRequest(BaseModel):
    """
    Supports either nested coordinates:
      {"origin": {"lat": 25.5788, "lng": 91.8933}, "destination": {"lat": 25.2750, "lng": 91.7323}}
    or flat coordinates:
      {"origin_lat": 25.5788, "origin_lng": 91.8933, "destination_lat": 25.2750, "destination_lng": 91.7323}
    plus optional preference ("shortest", "fastest", "balanced").
    """

    model_config = ConfigDict(extra="forbid")

    origin: CoordinatePoint | None = None
    destination: CoordinatePoint | None = None
    origin_lat: float | None = None
    origin_lng: float | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    preference: RoutePreferenceType = Field(
        default="balanced",
        description="Route evaluation preference ('shortest', 'fastest', or 'balanced')",
    )
    scope: Literal["regional", "india"] = Field(
        default="regional",
        description="Routing scope: 'regional' enforces strict 3 km local graph snapping; 'india' routes across all of India.",
    )

    @field_validator("origin_lat", "destination_lat", mode="before")
    @classmethod
    def validate_flat_lat(cls, v: Any) -> float | None:
        if v is None:
            return None
        return _check_finite_coord(v, "latitude", -90.0, 90.0)

    @field_validator("origin_lng", "destination_lng", mode="before")
    @classmethod
    def validate_flat_lng(cls, v: Any) -> float | None:
        if v is None:
            return None
        return _check_finite_coord(v, "longitude", -180.0, 180.0)

    @model_validator(mode="after")
    def normalize_coordinates(self) -> "RouteRequest":
        if self.origin is None:
            if self.origin_lat is not None and self.origin_lng is not None:
                self.origin = CoordinatePoint(lat=self.origin_lat, lng=self.origin_lng)
            else:
                raise ValueError(
                    "Origin coordinates are required: provide either 'origin' ({lat, lng}) "
                    "or both 'origin_lat' and 'origin_lng'."
                )
        else:
            self.origin_lat = self.origin.lat
            self.origin_lng = self.origin.lng

        if self.destination is None:
            if self.destination_lat is not None and self.destination_lng is not None:
                self.destination = CoordinatePoint(
                    lat=self.destination_lat, lng=self.destination_lng
                )
            else:
                raise ValueError(
                    "Destination coordinates are required: provide either 'destination' ({lat, lng}) "
                    "or both 'destination_lat' and 'destination_lng'."
                )
        else:
            self.destination_lat = self.destination.lat
            self.destination_lng = self.destination.lng

        return self


class SnapInfoResponse(BaseModel):
    label: str
    query_lat: float
    query_lng: float
    node_id: int
    node_lat: float
    node_lng: float
    snap_distance_m: float


class GeoJSONLineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]


class SingleRouteResponse(BaseModel):
    route_type: str
    optimization_weight: str
    node_ids: list[int]
    num_nodes: int
    distance_km: float
    estimated_duration_min: float
    duration_is_estimate: bool
    duration_estimate_note: str
    data_provenance: str | None = None
    estimation_limitations: list[str] | None = None
    merged_route_types: list[str] | None = None
    edge_summary: dict[str, Any] | None = None
    weather: dict[str, Any] | None = None
    disruptions: dict[str, Any] | None = None
    geometry: GeoJSONLineString


class RoutePairResponse(BaseModel):
    shortest: SingleRouteResponse
    estimated_fastest: SingleRouteResponse
    alternative_corridor: SingleRouteResponse | None = None


class RouteCalculationResponse(BaseModel):
    origin: SnapInfoResponse
    destination: SnapInfoResponse
    max_snap_distance_m: float
    travel_time_disclaimer: str
    region_info: dict[str, Any] | None = None
    routes: RoutePairResponse
    alternatives: list[SingleRouteResponse] | None = None
    evaluation: dict[str, Any] | None = None
    ml_ranking: dict[str, Any] | None = None
    weather_summary: dict[str, Any] | None = None
    disruptions_summary: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    graph_loaded: bool
    graph_path: str
    nodes: int | None = None
    directed_edges: int | None = None
    max_snap_distance_m: float | None = None
    load_count: int | None = None
    detail: str | None = None


class GeocodeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Location search text or 'lat, lng' coordinate string")
    limit: int = Field(default=6, ge=1, le=12, description="Maximum number of results to return")


class DisruptionRouteCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coordinates: list[list[float]] = Field(
        ..., description="List of [lng, lat] coordinate pairs along route polyline"
    )


class DemandZonesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_clusters: int = Field(
        default=4,
        description="Number of K-Means demand clusters (must be between 1 and dataset_size)",
    )
    random_state: int = Field(
        default=42,
        description="Random seed for reproducible K-Means initialization",
    )

    @field_validator("n_clusters", mode="before")
    @classmethod
    def validate_n_clusters(cls, v: Any) -> int:
        val = _check_strict_int(v, "n_clusters")
        if val < 1:
            raise ValueError(f"n_clusters must be a positive integer >= 1, got {val}.")
        return val

    @field_validator("random_state", mode="before")
    @classmethod
    def validate_random_state(cls, v: Any) -> int:
        return _check_strict_int(v, "random_state")


class DataProvenanceResponse(BaseModel):
    data_sources: list[str]
    is_synthetic_demo: bool
    provenance_note: str


class CoordinateProjectionResponse(BaseModel):
    input_crs: str
    clustering_crs: str
    clustering_units: str
    explanation: str
    limitations: list[str]


class ClusteringEvaluationMetricsResponse(BaseModel):
    inertia_m2: float
    silhouette_score: float | None = None
    davies_bouldin_score: float | None = None
    metrics_omitted_reason: str | None = None
    interpretation_note: str


class ClusterSummaryResponse(BaseModel):
    cluster_id: int
    center_lat: float
    center_lng: float
    center_easting_m: float
    center_northing_m: float
    demand_weighted_center_lat: float
    demand_weighted_center_lng: float
    point_count: int
    total_demand_units: float
    mean_demand_units: float
    demand_share_pct: float
    demand_weighted_priority_index: float
    priority_breakdown: dict[str, int]
    mean_distance_to_center_m: float
    max_distance_to_center_m: float


class AssignedDemandPointResponse(BaseModel):
    point_index: int
    latitude: float
    longitude: float
    demand_units: float
    priority: str
    priority_weight: float
    data_source: str
    cluster_id: int
    easting_m: float
    northing_m: float
    distance_to_cluster_center_m: float


class DemandZonesResponse(BaseModel):
    model: str
    n_clusters: int
    random_state: int
    dataset_size: int
    total_demand_units: float
    data_provenance: DataProvenanceResponse
    coordinate_projection: CoordinateProjectionResponse
    evaluation_metrics: ClusteringEvaluationMetricsResponse
    clusters: list[ClusterSummaryResponse]
    points: list[AssignedDemandPointResponse]


HTTP_422_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


# Exception handlers — return readable JSON errors and never leak stack traces
@app.exception_handler(InvalidCoordinateError)
async def handle_invalid_coordinate_error(
    _request: Request, exc: InvalidCoordinateError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "invalid_coordinates",
            "detail": str(exc),
        },
    )


@app.exception_handler(EmptyGeocodeQueryError)
async def handle_empty_geocode_query_error(
    _request: Request, exc: EmptyGeocodeQueryError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "empty_geocode_query",
            "detail": str(exc),
        },
    )


@app.exception_handler(InvalidCoordinateQueryError)
async def handle_invalid_coord_query_error(
    _request: Request, exc: InvalidCoordinateQueryError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "invalid_coordinates",
            "detail": str(exc),
        },
    )


@app.exception_handler(GeocodingError)
async def handle_geocoding_error(
    _request: Request, exc: GeocodingError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "geocoding_error",
            "detail": str(exc),
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    messages = []
    for err in exc.errors():
        loc = " -> ".join(str(part) for part in err.get("loc", []))
        msg = err.get("msg", "Invalid input")
        messages.append(f"{loc}: {msg}" if loc else msg)

    if request.url.path.startswith("/api/demand-zones"):
        error_code = "invalid_cluster_configuration"
    elif request.url.path.startswith("/api/geocode"):
        error_code = "invalid_geocode_request"
    else:
        error_code = "invalid_coordinates"

    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": error_code,
            "detail": "; ".join(messages),
        },
    )


@app.exception_handler(OutOfCoverageError)
async def handle_out_of_coverage_error(
    _request: Request, exc: OutOfCoverageError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "out_of_coverage",
            "detail": str(exc),
        },
    )


@app.exception_handler(UnreachableDestinationError)
async def handle_unreachable_destination_error(
    _request: Request, exc: UnreachableDestinationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "unreachable_destination",
            "detail": str(exc),
        },
    )


@app.exception_handler(GraphFileNotFoundError)
async def handle_graph_not_found_error(
    _request: Request, exc: GraphFileNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "graph_unavailable",
            "detail": str(exc),
        },
    )


@app.exception_handler(RouteEngineError)
async def handle_route_engine_error(
    _request: Request, exc: RouteEngineError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "route_engine_error",
            "detail": str(exc),
        },
    )


@app.exception_handler(InvalidClusterConfigurationError)
async def handle_invalid_cluster_config_error(
    _request: Request, exc: InvalidClusterConfigurationError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "invalid_cluster_configuration",
            "detail": str(exc),
        },
    )


@app.exception_handler(InsufficientDemandPointsError)
async def handle_insufficient_demand_points_error(
    _request: Request, exc: InsufficientDemandPointsError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "insufficient_demand_points",
            "detail": str(exc),
        },
    )


@app.exception_handler(InvalidDemandRecordError)
async def handle_invalid_demand_record_error(
    _request: Request, exc: InvalidDemandRecordError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "invalid_demand_record",
            "detail": str(exc),
        },
    )


@app.exception_handler(EmptyDemandDatasetError)
async def handle_empty_demand_dataset_error(
    _request: Request, exc: EmptyDemandDatasetError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_STATUS,
        content={
            "error": "empty_demand_dataset",
            "detail": str(exc),
        },
    )


@app.exception_handler(DemandClusteringError)
async def handle_demand_clustering_error(
    _request: Request, exc: DemandClusteringError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "demand_clustering_error",
            "detail": str(exc),
        },
    )


@app.get("/health", response_model=HealthResponse)
def health_check(request: Request) -> HealthResponse:
    """Return API status and whether the processed road graph is loaded."""
    engine: RouteEngine | None = getattr(request.app.state, "route_engine", None)
    startup_error: Exception | None = getattr(request.app.state, "startup_error", None)

    if engine is None and startup_error is None:
        try:
            engine = get_cached_route_engine()
            request.app.state.route_engine = engine
        except RouteEngineError as exc:
            startup_error = exc
            request.app.state.startup_error = exc

    if engine is not None:
        return HealthResponse(
            status="ok",
            graph_loaded=True,
            graph_path=str(engine.graph_path),
            nodes=int(engine.graph.number_of_nodes()),
            directed_edges=int(engine.graph.number_of_edges()),
            max_snap_distance_m=float(engine.max_snap_distance_m),
            load_count=int(engine.load_count),
            detail="Processed road network loaded and ready.",
        )

    return HealthResponse(
        status="degraded",
        graph_loaded=False,
        graph_path=str(DEFAULT_PROCESSED_GRAPH_PATH),
        detail=str(startup_error) if startup_error else "Road network not loaded.",
    )


@app.post("/api/routes", response_model=RouteCalculationResponse)
def calculate_routes_endpoint(
    payload: RouteRequest,
    engine: RouteEngine = Depends(get_route_engine),
) -> dict[str, Any]:
    """
    Calculate the shortest-distance route, estimated-fastest route, deterministic
    component & overall evaluation scores, and experimental ML ranking comparison.
    Supports both strict local GraphML routing (scope='regional') and Pan-India
    OpenStreetMap routing across all Indian states and territories (scope='india').
    """
    assert payload.origin is not None and payload.destination is not None
    if payload.scope == "india":
        pan_india = get_cached_pan_india_service()
        return pan_india.calculate_pan_india_routes(
            origin_lat=payload.origin.lat,
            origin_lng=payload.origin.lng,
            destination_lat=payload.destination.lat,
            destination_lng=payload.destination.lng,
            preference=payload.preference,
            local_engine=engine,
        )
    return engine.calculate_routes(
        origin_lat=payload.origin.lat,
        origin_lng=payload.origin.lng,
        destination_lat=payload.destination.lat,
        destination_lng=payload.destination.lng,
        preference=payload.preference,
    )


@app.get("/api/geocode")
def geocode_get_endpoint(
    q: str = Query(default="", description="Place name or 'lat, lng' coordinate string"),
    limit: int = Query(default=6, ge=1, le=12),
    engine: RouteEngine = Depends(get_route_engine),
) -> dict[str, Any]:
    """
    Search for origin or destination locations by text or coordinates, returning
    resolved coordinates and road-network coverage diagnostics.
    """
    service = get_cached_geocoding_service()
    return service.search_places(query=q, limit=limit, active_engine=engine)


@app.post("/api/geocode")
def geocode_post_endpoint(
    payload: GeocodeSearchRequest,
    engine: RouteEngine = Depends(get_route_engine),
) -> dict[str, Any]:
    """POST variant for text/coordinate location lookup and road-network coverage validation."""
    service = get_cached_geocoding_service()
    return service.search_places(
        query=payload.query, limit=payload.limit, active_engine=engine
    )


@app.get("/api/geocode/suggestions")
def geocode_suggestions_endpoint(
    engine: RouteEngine = Depends(get_route_engine),
) -> dict[str, Any]:
    """Return featured North-East India logistics hubs with live road-graph coverage status."""
    service = get_cached_geocoding_service()
    items = service.list_default_suggestions(active_engine=engine)
    return {
        "count": len(items),
        "suggestions": items,
    }


@app.get("/api/regions")
def list_regions_endpoint(
    engine: RouteEngine = Depends(get_route_engine),
) -> dict[str, Any]:
    """List all configured regional road graphs, their coverage bounds, and installation status."""
    mgr = get_cached_region_manager()
    mgr.register_engine_instance(mgr.default_region_id, engine)
    regions = mgr.list_regions_status()
    return {
        "default_region_id": mgr.default_region_id,
        "max_snap_distance_m": engine.max_snap_distance_m,
        "regions": regions,
    }


@app.get("/api/ml-ranking/evaluation")
def ml_ranking_evaluation_endpoint() -> dict[str, Any]:
    """
    Return the experimental Pairwise Route-Ranking ML evaluation report comparing
    the model against deterministic baselines on held-out spatial query groups.
    """
    ranker = get_cached_ml_ranker()
    if ranker.evaluation_summary is None:
        return ranker.fit_and_evaluate()
    return ranker.evaluation_summary


@app.post("/api/demand-zones", response_model=DemandZonesResponse)
def calculate_demand_zones_endpoint(
    payload: DemandZonesRequest | None = Body(default=None),
) -> dict[str, Any]:
    """
    Fit K-Means demand-zone clusters on the synthetic demonstration dataset
    (backend/data/sample_delivery_demand.csv) using projected UTM Zone 46N metric coordinates.
    """
    params = payload if isinstance(payload, DemandZonesRequest) else DemandZonesRequest()
    try:
        records = get_cached_sample_demand_records()
    except FileNotFoundError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "demand_dataset_unavailable",
                "detail": str(exc),
            },
        )  # type: ignore[return-value]

    clusterer = DemandZoneClusterer(
        n_clusters=params.n_clusters,
        random_state=params.random_state,
    )
    return clusterer.fit_predict(records)


@app.get("/api/weather")
def get_weather_endpoint(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    location_name: str = Query(default=""),
) -> dict[str, Any]:
    """Fetch live or cached atmospheric weather observation and 6h forecast from Open-Meteo."""
    svc = get_cached_weather_service()
    return svc.fetch_point_weather(lat=lat, lng=lng, location_name=location_name)


@app.get("/api/disruptions")
def get_disruptions_endpoint(
    active_only: bool = Query(default=True),
) -> dict[str, Any]:
    """List verified regional road disruption, slope debris, and bridge load-limit advisories."""
    svc = get_cached_disruptions_service()
    disruptions = svc.list_active_disruptions() if active_only else svc._disruptions
    return {
        "count": len(disruptions),
        "disruptions": disruptions,
        "data_source": "Official Regional Road Advisories (NHIDCL / Meghalaya PWD / SDMA / BRO)",
    }


@app.post("/api/disruptions/check-route")
def check_route_disruptions_endpoint(
    payload: DisruptionRouteCheckRequest,
) -> dict[str, Any]:
    """Check spatial intersection between candidate route polyline and verified active hazard zones."""
    svc = get_cached_disruptions_service()
    return svc.evaluate_route_disruptions(payload.coordinates)


# ==============================================================================
# Module D & E: Road Accessibility Monitoring & Field Reporting Endpoints
# ==============================================================================


class IncidentReportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=5, max_length=2000)
    incident_type: Literal[
        "road_blockage",
        "flood",
        "landslide",
        "bridge_damage",
        "road_damage",
        "other",
    ]
    severity: Literal["low", "moderate", "severe", "critical"]
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    district: str = Field(..., min_length=2, max_length=100)
    location_name: str = Field(..., min_length=2, max_length=150)
    reporter_name: str = Field(..., min_length=2, max_length=100)
    reporter_role: str = Field(default="field_worker", max_length=50)
    contact_number: str | None = Field(default=None, max_length=30)
    photo_url: str | None = Field(default=None, max_length=500)


class IncidentReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_status: Literal["verified", "rejected", "resolved"]
    actor: str = Field(..., min_length=2, max_length=100)
    review_notes: str = Field(..., min_length=3, max_length=1000)
    cascade_to_segment: Literal["open", "restricted", "blocked"] | None = None


class SegmentStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_status: Literal["open", "restricted", "blocked", "unknown"]
    actor: str = Field(..., min_length=2, max_length=100)
    restriction_details: str | None = Field(default=None, max_length=500)
    review_notes: str | None = Field(default=None, max_length=1000)


@app.get("/api/accessibility/segments")
def list_segments_endpoint(
    district: str | None = Query(default=None),
    status: Literal["open", "restricted", "blocked", "unknown"] | None = Query(default=None),
) -> dict[str, Any]:
    """List monitored road corridors with optional district and status filters."""
    svc = get_cached_accessibility_service()
    segments = svc.list_segments(district=district, status=status)
    return {
        "count": len(segments),
        "segments": segments,
        "disclaimer": "OFFICIAL CORRIDOR STATUSES. Segment closures require administrative review.",
    }


@app.get("/api/accessibility/segments/{segment_id}")
def get_segment_endpoint(segment_id: str) -> dict[str, Any]:
    """Fetch details of a single monitored road corridor."""
    svc = get_cached_accessibility_service()
    segment = svc.get_segment(segment_id)
    if not segment:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "segment_not_found", "detail": f"Road segment '{segment_id}' not found."},
        )
    return segment


@app.patch("/api/accessibility/segments/{segment_id}/status")
def update_segment_status_endpoint(
    segment_id: str,
    payload: SegmentStatusUpdateRequest,
) -> dict[str, Any]:
    """Update a road segment's operational status and record an immutable audit entry."""
    svc = get_cached_accessibility_service()
    try:
        updated = svc.update_segment_status(
            segment_id=segment_id,
            new_status=payload.new_status,
            actor=payload.actor,
            restriction_details=payload.restriction_details,
            review_notes=payload.review_notes,
        )
        return {"status": "success", "segment": updated}
    except KeyError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "segment_not_found", "detail": str(exc)},
        )


@app.get("/api/accessibility/incidents")
def list_incidents_endpoint(
    status: Literal["pending", "verified", "rejected", "resolved"] | None = Query(default=None),
    incident_type: Literal[
        "road_blockage",
        "flood",
        "landslide",
        "bridge_damage",
        "road_damage",
        "other",
    ]
    | None = Query(default=None),
    district: str | None = Query(default=None),
) -> dict[str, Any]:
    """List field incident reports with optional filters."""
    svc = get_cached_accessibility_service()
    incidents = svc.list_incidents(status=status, incident_type=incident_type, district=district)
    return {
        "count": len(incidents),
        "incidents": incidents,
    }


@app.get("/api/accessibility/incidents/{report_id}")
def get_incident_endpoint(report_id: str) -> dict[str, Any]:
    """Get single incident report and its audit history."""
    svc = get_cached_accessibility_service()
    incident = svc.get_incident(report_id)
    if not incident:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "incident_not_found", "detail": f"Incident '{report_id}' not found."},
        )
    audit = svc.list_audit_logs(entity_type="incident", entity_id=report_id)
    return {"incident": incident, "audit_trail": audit}


@app.post("/api/accessibility/reports")
def submit_incident_report_endpoint(
    payload: IncidentReportCreateRequest,
) -> dict[str, Any]:
    """
    Submit a field incident report.
    Reports always enter 'pending' status until verified by an authorized reviewer.
    """
    svc = get_cached_accessibility_service()
    incident = svc.submit_incident_report(
        title=payload.title,
        description=payload.description,
        incident_type=payload.incident_type,
        severity=payload.severity,
        latitude=payload.latitude,
        longitude=payload.longitude,
        district=payload.district,
        location_name=payload.location_name,
        reporter_name=payload.reporter_name,
        reporter_role=payload.reporter_role,
        contact_number=payload.contact_number,
        photo_url=payload.photo_url,
    )
    return {
        "status": "created",
        "message": "Incident report submitted successfully and placed in review queue.",
        "incident": incident,
    }


@app.patch("/api/accessibility/incidents/{report_id}/status")
def review_incident_endpoint(
    report_id: str,
    payload: IncidentReviewRequest,
) -> dict[str, Any]:
    """
    Review and verify/reject/resolve an incident report.
    Records reviewer name, notes, and timestamp in the audit trail.
    """
    svc = get_cached_accessibility_service()
    try:
        reviewed = svc.review_incident(
            report_id=report_id,
            new_status=payload.new_status,
            actor=payload.actor,
            review_notes=payload.review_notes,
            cascade_to_segment=payload.cascade_to_segment,
        )
        return {
            "status": "success",
            "message": f"Incident {report_id} status updated to {payload.new_status}.",
            "incident": reviewed,
        }
    except KeyError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "incident_not_found", "detail": str(exc)},
        )


@app.get("/api/accessibility/audit-log")
def list_audit_log_endpoint(
    entity_type: Literal["incident", "road_segment"] | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """Retrieve immutable audit log of status changes and administrative reviews."""
    svc = get_cached_accessibility_service()
    logs = svc.list_audit_logs(entity_type=entity_type, entity_id=entity_id, limit=limit)
    return {"count": len(logs), "logs": logs}


@app.post("/api/accessibility/upload-photo")
async def upload_photo_endpoint(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload and validate an incident photograph (JPG, PNG, WebP up to 5 MB)."""
    svc = get_cached_accessibility_service()
    content = await file.read()
    try:
        photo_url = svc.save_uploaded_photo(file.filename or "photo.jpg", content)
        return {"photo_url": photo_url, "filename": file.filename, "size_bytes": len(content)}
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_photo_upload", "detail": str(exc)},
        )


class PhotoUploadBase64Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(default="incident.jpg", max_length=100)
    data_base64: str = Field(..., min_length=10)


@app.post("/api/accessibility/upload-photo-base64")
def upload_photo_base64_endpoint(payload: PhotoUploadBase64Request) -> dict[str, Any]:
    """Upload and validate an incident photograph as base64 string (max 5 MB)."""
    raw_b64 = payload.data_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    try:
        content = base64.b64decode(raw_b64)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_base64", "detail": f"Could not decode base64: {exc}"},
        )
    svc = get_cached_accessibility_service()
    try:
        photo_url = svc.save_uploaded_photo(payload.filename, content)
        return {"photo_url": photo_url, "filename": payload.filename, "size_bytes": len(content)}
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_photo_upload", "detail": str(exc)},
        )


@app.get("/api/accessibility/photos/{filename}")
def serve_photo_endpoint(filename: str) -> Any:
    """Serve saved incident evidence photograph."""
    safe_path = UPLOADS_DIR / os.path.basename(filename)
    if not safe_path.is_file():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "photo_not_found", "detail": "Photograph not found."},
        )
    return FileResponse(str(safe_path))


# ==============================================================================
# Module F: GPS Vehicle and Delivery Tracking Endpoints
# ==============================================================================


class VehicleRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_id: str = Field(..., min_length=3, max_length=30)
    name: str = Field(..., min_length=2, max_length=100)
    vehicle_type: Literal["4x4", "Van", "Heavy Truck", "Electric Van", "Pickup"]
    capacity_kg: float = Field(..., gt=0.0)
    assigned_driver_name: str = Field(..., min_length=2, max_length=100)
    assigned_driver_contact: str | None = Field(default=None, max_length=30)
    initial_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    initial_lng: float | None = Field(default=None, ge=-180.0, le=180.0)


class DeliveryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_id: str = Field(..., min_length=3, max_length=30)
    title: str = Field(..., min_length=3, max_length=150)
    goods_category: Literal[
        "Medical Supplies",
        "Food Supplies",
        "Relief Materials",
        "General Cargo",
        "Vaccines / Cold Chain",
    ]
    priority: Literal["Emergency", "High", "Normal", "Low"]
    origin_name: str = Field(..., min_length=2, max_length=150)
    origin_lat: float = Field(..., ge=-90.0, le=90.0)
    origin_lng: float = Field(..., ge=-180.0, le=180.0)
    destination_name: str = Field(..., min_length=2, max_length=150)
    destination_lat: float = Field(..., ge=-90.0, le=90.0)
    destination_lng: float = Field(..., ge=-180.0, le=180.0)
    planned_distance_km: float = Field(..., gt=0.0)
    planned_duration_minutes: float = Field(..., gt=0.0)
    planned_route_geometry: list[list[float]] = Field(..., min_length=2)
    dispatch_immediately: bool = True


class DeliveryStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_status: Literal[
        "scheduled",
        "dispatched",
        "in_transit",
        "delayed",
        "delivered",
        "interrupted",
    ]
    delay_reason: str | None = Field(default=None, max_length=500)


class TelemetryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_id: str = Field(..., min_length=3, max_length=30)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    speed_kph: float = Field(default=0.0, ge=0.0, le=160.0)
    bearing: float = Field(default=0.0, ge=0.0, le=360.0)
    delivery_id: str | None = Field(default=None, max_length=50)
    source: Literal["real_gps", "simulated_demo"] = "real_gps"


class SimulateStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    progress_step_pct: float = Field(default=5.0, gt=0.0, le=50.0)
    simulate_deviation: bool = False


@app.get("/api/tracking/vehicles")
def list_vehicles_endpoint(
    vehicle_type: Literal["4x4", "Van", "Heavy Truck", "Electric Van", "Pickup"] | None = Query(default=None),
) -> dict[str, Any]:
    """List registered vehicles with optional vehicle type filter."""
    svc = get_cached_tracking_service()
    vehicles = svc.list_vehicles(vehicle_type=vehicle_type)
    return {"count": len(vehicles), "vehicles": vehicles}


@app.post("/api/tracking/vehicles")
def register_vehicle_endpoint(payload: VehicleRegisterRequest) -> dict[str, Any]:
    """Register a new vehicle in the logistics fleet catalog."""
    svc = get_cached_tracking_service()
    try:
        vehicle = svc.register_vehicle(
            vehicle_id=payload.vehicle_id,
            name=payload.name,
            vehicle_type=payload.vehicle_type,
            capacity_kg=payload.capacity_kg,
            assigned_driver_name=payload.assigned_driver_name,
            assigned_driver_contact=payload.assigned_driver_contact,
            initial_lat=payload.initial_lat,
            initial_lng=payload.initial_lng,
        )
        return {"status": "created", "vehicle": vehicle}
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "vehicle_registration_failed", "detail": str(exc)},
        )


@app.get("/api/tracking/vehicles/{vehicle_id}")
def get_vehicle_endpoint(vehicle_id: str) -> dict[str, Any]:
    """Fetch details of a single vehicle."""
    svc = get_cached_tracking_service()
    vehicle = svc.get_vehicle(vehicle_id)
    if not vehicle:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "vehicle_not_found", "detail": f"Vehicle '{vehicle_id}' not found."},
        )
    return vehicle


@app.get("/api/tracking/deliveries")
def list_deliveries_endpoint(
    status: Literal[
        "scheduled",
        "dispatched",
        "in_transit",
        "delayed",
        "delivered",
        "interrupted",
    ]
    | None = Query(default=None),
    vehicle_id: str | None = Query(default=None),
) -> dict[str, Any]:
    """List deliveries with optional status or vehicle filter."""
    svc = get_cached_tracking_service()
    deliveries = svc.list_deliveries(status=status, vehicle_id=vehicle_id)
    return {"count": len(deliveries), "deliveries": deliveries}


@app.post("/api/tracking/deliveries")
def create_delivery_endpoint(payload: DeliveryCreateRequest) -> dict[str, Any]:
    """Create and dispatch a new delivery mission."""
    svc = get_cached_tracking_service()
    try:
        geometry_tuples = [(pt[0], pt[1]) for pt in payload.planned_route_geometry]
        delivery = svc.create_delivery(
            vehicle_id=payload.vehicle_id,
            title=payload.title,
            goods_category=payload.goods_category,
            priority=payload.priority,
            origin_name=payload.origin_name,
            origin_lat=payload.origin_lat,
            origin_lng=payload.origin_lng,
            destination_name=payload.destination_name,
            destination_lat=payload.destination_lat,
            destination_lng=payload.destination_lng,
            planned_distance_km=payload.planned_distance_km,
            planned_duration_minutes=payload.planned_duration_minutes,
            planned_route_geometry=geometry_tuples,
            dispatch_immediately=payload.dispatch_immediately,
        )
        return {"status": "created", "delivery": delivery}
    except KeyError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "vehicle_not_found", "detail": str(exc)},
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_delivery_payload", "detail": str(exc)},
        )


@app.get("/api/tracking/deliveries/{delivery_id}")
def get_delivery_endpoint(delivery_id: str) -> dict[str, Any]:
    """Get single delivery details."""
    svc = get_cached_tracking_service()
    delivery = svc.get_delivery(delivery_id)
    if not delivery:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "delivery_not_found", "detail": f"Delivery '{delivery_id}' not found."},
        )
    return delivery


@app.patch("/api/tracking/deliveries/{delivery_id}/status")
def update_delivery_status_endpoint(
    delivery_id: str,
    payload: DeliveryStatusUpdateRequest,
) -> dict[str, Any]:
    """Update delivery operational status (e.g. mark delayed or delivered)."""
    svc = get_cached_tracking_service()
    try:
        updated = svc.update_delivery_status(
            delivery_id=delivery_id,
            new_status=payload.new_status,
            delay_reason=payload.delay_reason,
        )
        return {"status": "success", "delivery": updated}
    except KeyError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "delivery_not_found", "detail": str(exc)},
        )


@app.post("/api/tracking/telemetry")
def record_telemetry_endpoint(payload: TelemetryUpdateRequest) -> dict[str, Any]:
    """
    Secure GPS telemetry update endpoint.
    Computes distance to planned corridor and flags route deviations (> 500m).
    """
    svc = get_cached_tracking_service()
    try:
        res = svc.record_telemetry(
            vehicle_id=payload.vehicle_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed_kph=payload.speed_kph,
            bearing=payload.bearing,
            delivery_id=payload.delivery_id,
            source=payload.source,
        )
        return res
    except KeyError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "vehicle_not_found", "detail": str(exc)},
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_telemetry_payload", "detail": str(exc)},
        )


@app.post("/api/tracking/deliveries/{delivery_id}/simulate-step")
def simulate_delivery_step_endpoint(
    delivery_id: str,
    payload: SimulateStepRequest | None = Body(default=None),
) -> dict[str, Any]:
    """
    Advance delivery vehicle along planned geometry for demonstration simulation.
    Explicitly labeled as demonstration mode to maintain academic integrity.
    """
    svc = get_cached_tracking_service()
    step_pct = payload.progress_step_pct if payload else 5.0
    sim_dev = payload.simulate_deviation if payload else False
    try:
        res = svc.step_simulated_telemetry(
            delivery_id=delivery_id,
            progress_step_pct=step_pct,
            simulate_deviation=sim_dev,
        )
        return res
    except KeyError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "delivery_not_found", "detail": str(exc)},
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "simulation_failed", "detail": str(exc)},
        )


@app.get("/api/tracking/vehicles/{vehicle_id}/telemetry-history")
def get_telemetry_history_endpoint(
    vehicle_id: str,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    """Retrieve telemetry log history for a vehicle."""
    svc = get_cached_tracking_service()
    history = svc.get_telemetry_history(vehicle_id=vehicle_id, limit=limit)
    return {"count": len(history), "history": history}


# ==============================================================================
# Module G: Alerts and Notifications Endpoints
# ==============================================================================


class AlertReadUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_read: bool = True


@app.get("/api/notifications")
def list_notifications_endpoint(
    unread_only: bool = Query(default=False),
    category: Literal[
        "road_closure",
        "landslide",
        "flood",
        "severe_weather",
        "vehicle_delay",
        "route_disruption",
        "route_deviation",
    ]
    | None = Query(default=None),
    severity: Literal["info", "warning", "severe", "critical"] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Retrieve operational alerts and notifications with optional filtering."""
    svc = get_cached_alerts_service()
    alerts = svc.list_alerts(
        unread_only=unread_only,
        category=category,
        severity=severity,
        limit=limit,
    )
    unread_count = svc.get_unread_count()
    return {
        "count": len(alerts),
        "unread_count": unread_count,
        "alerts": alerts,
    }


@app.get("/api/notifications/unread-count")
def get_unread_count_endpoint() -> dict[str, Any]:
    """Lightweight endpoint returning current unread alert count for badge counter."""
    svc = get_cached_alerts_service()
    return {"unread_count": svc.get_unread_count()}


@app.patch("/api/notifications/{alert_id}/read")
def mark_notification_read_endpoint(
    alert_id: str,
    payload: AlertReadUpdateRequest | None = Body(default=None),
) -> dict[str, Any]:
    """Mark an individual notification as read or unread."""
    svc = get_cached_alerts_service()
    is_read = payload.is_read if payload else True
    try:
        updated = svc.mark_alert_read(alert_id=alert_id, is_read=is_read)
        return {"status": "success", "alert": updated, "unread_count": svc.get_unread_count()}
    except KeyError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "alert_not_found", "detail": str(exc)},
        )


@app.post("/api/notifications/mark-all-read")
def mark_all_notifications_read_endpoint() -> dict[str, Any]:
    """Mark all unread notifications as read."""
    svc = get_cached_alerts_service()
    marked_count = svc.mark_all_read()
    return {
        "status": "success",
        "marked_count": marked_count,
        "unread_count": 0,
    }


@app.post("/api/notifications/sync-triggers")
def sync_notification_triggers_endpoint() -> dict[str, Any]:
    """
    Evaluate automated triggers across Accessibility, Disruptions, and Tracking modules.
    Generates deduplicated operational alerts.
    """
    alerts_svc = get_cached_alerts_service()
    acc_svc = get_cached_accessibility_service()
    dis_svc = get_cached_disruptions_service()
    track_svc = get_cached_tracking_service()

    sync_result = alerts_svc.sync_automated_triggers(
        accessibility_svc=acc_svc,
        disruptions_svc=dis_svc,
        tracking_svc=track_svc,
    )
    return {
        "status": "success",
        "sync_result": sync_result,
    }


@app.get("/api/notifications/channels")
def get_notification_channels_endpoint() -> dict[str, Any]:
    """List operational vs extensible notification channel adapters with honest provenance."""
    svc = get_cached_alerts_service()
    return svc.get_channel_registry()




