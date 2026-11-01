"""
NER SmartRoute — Core Routing & Machine Learning Algorithms Package
Contains graph pathfinding, multi-criteria scoring, and ranking ML models.
"""

from .route_engine import RouteEngine, RouteEngineError, OutOfCoverageError, MAX_SNAP_DISTANCE_M
from .route_scoring import evaluate_candidate_routes, RoutePreferenceType, PREFERENCE_WEIGHTS
from .route_ranking_ml import PairwiseRouteRanker
from .region_manager import RegionGraphManager
from .demand_clustering import DemandZoneClusterer
from .pan_india_routing import PanIndiaRoutingService

__all__ = [
    "RouteEngine",
    "RouteEngineError",
    "OutOfCoverageError",
    "MAX_SNAP_DISTANCE_M",
    "evaluate_candidate_routes",
    "RoutePreferenceType",
    "PREFERENCE_WEIGHTS",
    "PairwiseRouteRanker",
    "RegionGraphManager",
    "DemandZoneClusterer",
    "PanIndiaRoutingService",
]

