from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
import math
from typing import Any, Literal

from fastapi import Body, Depends, FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
)
from route_scoring import RoutePreferenceType

VITE_DEV_ORIGIN = "http://localhost:5173"
VITE_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


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

# Restrict CORS strictly to the local Vite development server origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=VITE_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
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
