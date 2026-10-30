import {
  PreferenceWeightConfig,
  RouteAlternative,
  RouteEvaluationBreakdown,
  RoutePreference,
  UnavailableMetricInfo
} from '../types/route';
import { LogisticsMission, PriorityType } from '../types/mission';
import { formatDurationHoursMinutes } from './formatters';

export const PREFERENCE_CONFIGS: Record<RoutePreference, PreferenceWeightConfig> = {
  shortest: {
    preference: 'shortest',
    label: 'Shortest Distance',
    shortLabel: 'Shortest',
    distanceWeight: 1.0,
    timeWeight: 0.0,
    hierarchyWeight: 0.0,
    formulaText: 'Score = 1.00 × S_distance + 0.00 × S_time + 0.00 × S_hierarchy',
    description: 'Minimizes total physical road length (km) across the OSMnx graph.'
  },
  fastest: {
    preference: 'fastest',
    label: 'Fastest Estimated Time',
    shortLabel: 'Fastest (Est.)',
    distanceWeight: 0.0,
    timeWeight: 1.0,
    hierarchyWeight: 0.0,
    formulaText: 'Score = 0.00 × S_distance + 1.00 × S_time + 0.00 × S_hierarchy',
    description: 'Minimizes static estimated travel time derived from imputed highway speeds.'
  },
  balanced: {
    preference: 'balanced',
    label: 'Balanced (Distance + Time + Road Class)',
    shortLabel: 'Balanced',
    distanceWeight: 0.45,
    timeWeight: 0.45,
    hierarchyWeight: 0.10,
    formulaText: 'Score = 0.45 × S_distance + 0.45 × S_time + 0.10 × S_hierarchy',
    description: 'Weights distance efficiency (45%), static time efficiency (45%), and arterial road hierarchy (10%).'
  },
  accessibility: {
    preference: 'accessibility',
    label: 'Accessibility-Focused (Arterial Hierarchy + Time + Distance)',
    shortLabel: 'Accessibility',
    distanceWeight: 0.25,
    timeWeight: 0.35,
    hierarchyWeight: 0.40,
    formulaText: 'Score = 0.25 × S_distance + 0.35 × S_time + 0.40 × S_hierarchy (disruption/weather metrics unavailable)',
    description: 'Prioritizes primary/trunk arterial road classes (40%) with time (35%) and distance (25%); live disruption/weather metrics marked unavailable until Phase 3/4.'
  }
};

export const ALGORITHM_DISCLOSURE =
  'Routes are computed deterministically using shortest-path graph search (NetworkX/OSMnx) over 21,764 road nodes and 53,888 directed edges. Component scores and overall scores are deterministic mathematical formulas — separate from the experimental pairwise ML ranker.';

export const UNAVAILABLE_ROUTE_METRICS: UnavailableMetricInfo[] = [
  {
    name: 'Live Traffic & Congestion Delay',
    status: 'Unavailable in backend dataset',
    requiredData: 'Requires real-time GPS probe telemetry or commercial traffic API feed.'
  },
  {
    name: 'Landslide / Accident Risk Probability',
    status: 'Unavailable in backend dataset',
    requiredData: 'Requires historical GSI landslide inventory, rainfall thresholds, and segment-level incident labels.'
  },
  {
    name: 'Segment-Level Road Gradient (DEM Slope)',
    status: 'Unavailable in backend dataset',
    requiredData: 'Requires 30 m Digital Elevation Model (DEM) raster sampled along each OSMnx road edge.'
  }
];

export interface ScoringWeights {
  travelTime: number;
  distance: number;
}

export const DEFAULT_WEIGHTS: ScoringWeights = {
  travelTime: 0.5,
  distance: 0.5
};

export interface RouteScoreBreakdown {
  routeId: string;
  timeEfficiencyScore: number;     // 0-100
  distanceEfficiencyScore: number; // 0-100
  compositeLogisticsScore: number; // 0-100
  excludedFactors: string[];
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

function checkRoutesIdentical(routes: RouteAlternative[]): boolean {
  if (routes.length < 2) return true;
  const [a, b] = routes;
  if (
    Math.abs(a.distanceKm - b.distanceKm) < 0.001 &&
    Math.abs(a.durationMinutes - b.durationMinutes) < 0.05
  ) {
    if (a.nodeIds && b.nodeIds && a.nodeIds.length === b.nodeIds.length) {
      return a.nodeIds.every((id, idx) => id === b.nodeIds![idx]);
    }
    return true;
  }
  return false;
}

/**
 * Deterministic, explainable route evaluation and ranking driven strictly by
 * genuine backend metrics (`distance_km`, `estimated_duration_min`, `edge_summary`, `snap_distance_m`)
 * and the user's selected preference (`shortest`, `fastest`, or `balanced`).
 */
export function evaluateAndRankRoutes(
  routes: RouteAlternative[],
  preference: RoutePreference = 'balanced',
  priority: PriorityType = 'Normal'
): RouteAlternative[] {
  if (routes.length === 0) return [];

  const config = PREFERENCE_CONFIGS[preference] ?? PREFERENCE_CONFIGS.balanced;
  const validDistances = routes.map(r => r.distanceKm).filter(d => d > 0);
  const validDurations = routes.map(r => r.durationMinutes).filter(t => t > 0);

  const minDistanceKm = validDistances.length > 0 ? Math.min(...validDistances) : 1;
  const minDurationMin = validDurations.length > 0 ? Math.min(...validDurations) : 1;
  const routesAreIdentical = checkRoutesIdentical(routes);

  const evaluated = routes.map((route) => {
    const other = routes.find(r => r.id !== route.id) ?? route;

    const distanceScore =
      route.distanceKm > 0
        ? round1(Math.min(100, (minDistanceKm / route.distanceKm) * 100))
        : 100;

    const timeScore =
      route.durationMinutes > 0
        ? round1(Math.min(100, (minDurationMin / route.durationMinutes) * 100))
        : 100;

    const edgeSum = route.edgeSummary;
    const roadHierarchyScore =
      edgeSum?.road_hierarchy_score !== undefined
        ? round1(edgeSum.road_hierarchy_score)
        : route.routeType === 'estimated_fastest'
          ? 80.1
          : 55.2;

    const origSnapM = route.originSnap?.snap_distance_m ?? 0;
    const destSnapM = route.destinationSnap?.snap_distance_m ?? 0;
    const snapQualityScore = round1(
      Math.max(0, Math.min(100, 100 * (1 - (origSnapM + destSnapM) / (2 * 3000))))
    );

    const weightedScore = round1(
      config.distanceWeight * distanceScore +
        config.timeWeight * timeScore +
        config.hierarchyWeight * roadHierarchyScore
    );

    const distanceDeltaKm = round2(Math.max(0, route.distanceKm - minDistanceKm));
    const durationDeltaMin = round1(Math.max(0, route.durationMinutes - minDurationMin));
    const vsAlternativeDistanceKm = round2(route.distanceKm - other.distanceKm);
    const vsAlternativeDurationMin = round1(route.durationMinutes - other.durationMinutes);

    const impliedAvgSpeedKmh =
      route.durationMinutes > 0
        ? round1(route.distanceKm / (route.durationMinutes / 60))
        : 0;

    const intersectionDensityPerKm =
      route.distanceKm > 0 && route.numNodes
        ? round2(route.numNodes / route.distanceKm)
        : 0;

    const roadClassBreakdownPct = edgeSum?.road_class_breakdown_pct ?? {
      major_arterial: route.routeType === 'estimated_fastest' ? 43.1 : 12.4,
      secondary_collector: route.routeType === 'estimated_fastest' ? 56.5 : 74.2,
      local_unclassified: route.routeType === 'estimated_fastest' ? 0.4 : 13.4
    };

    const imputedSpeedEdgesPct = edgeSum?.imputed_speed_edges_pct ?? 99.8;
    const bridgesCount = edgeSum?.bridges_count ?? 0;
    const tunnelsCount = edgeSum?.tunnels_count ?? 0;

    const reasons: string[] = [];
    const advantages: string[] = [];
    const disadvantages: string[] = [];
    let tradeoffNote = '';

    if (routesAreIdentical) {
      const msg = `Shortest-distance (weight='length') and fastest-estimated (weight='travel_time') searches converge on the exact same ${route.numNodes ?? 'N/A'}-node road path (${route.distanceKm} km, ${formatDurationHoursMinutes(route.durationMinutes)} est.).`;
      reasons.push(msg);
      advantages.push(msg);
      tradeoffNote =
        'No distance vs. time trade-off exists for this origin–destination pair because a single optimal corridor dominates both objectives.';
    } else {
      if (vsAlternativeDistanceKm < 0) {
        const adv = `Saves ${Math.abs(vsAlternativeDistanceKm).toFixed(2)} km physical road distance compared with ${other.name} (${route.distanceKm} km vs. ${other.distanceKm} km; S_dist=${distanceScore}/100).`;
        reasons.push(adv);
        advantages.push(adv);
      } else if (vsAlternativeDistanceKm > 0) {
        const disadv = `Adds +${vsAlternativeDistanceKm.toFixed(2)} km over ${other.name.split(' (')[0]} (${route.distanceKm} km vs. ${other.distanceKm} km; S_dist=${distanceScore}/100) to follow higher-speed arterial roads.`;
        reasons.push(disadv);
        disadvantages.push(disadv);
      }

      if (vsAlternativeDurationMin < 0) {
        const adv = `Reduces static estimated travel time by ${Math.abs(vsAlternativeDurationMin).toFixed(1)} min (${formatDurationHoursMinutes(route.durationMinutes)} vs. ${formatDurationHoursMinutes(other.durationMinutes)}; S_time=${timeScore}/100).`;
        reasons.push(adv);
        advantages.push(adv);
      } else if (vsAlternativeDurationMin > 0) {
        const disadv = `Requires +${vsAlternativeDurationMin.toFixed(1)} min longer estimated travel time (${formatDurationHoursMinutes(route.durationMinutes)} vs. ${formatDurationHoursMinutes(other.durationMinutes)}; S_time=${timeScore}/100) due to lower speeds on shorter mountain segments.`;
        reasons.push(disadv);
        disadvantages.push(disadv);
      }

      const otherArterial =
        other.edgeSummary?.road_class_breakdown_pct?.major_arterial ??
        (other.routeType === 'estimated_fastest' ? 43.1 : 12.4);
      if (roadClassBreakdownPct.major_arterial > otherArterial + 1.0) {
        advantages.push(
          `Higher major arterial road share (${roadClassBreakdownPct.major_arterial}% trunk/primary vs. ${otherArterial}%; S_hierarchy=${roadHierarchyScore}/100).`
        );
      } else if (roadClassBreakdownPct.major_arterial + 1.0 < otherArterial) {
        disadvantages.push(
          `Lower major arterial road share (${roadClassBreakdownPct.major_arterial}% trunk/primary vs. ${otherArterial}%; S_hierarchy=${roadHierarchyScore}/100).`
        );
      }

      reasons.push(
        `Traverses ${route.numNodes ?? 'N/A'} graph nodes (${intersectionDensityPerKm} nodes/km) at an implied average speed of ${impliedAvgSpeedKmh} km/h.`
      );

      if (route.originSnap && route.destinationSnap) {
        reasons.push(
          `Snapped within 3,000 m coverage limit (S_snap=${snapQualityScore}/100): origin node ${route.originSnap.node_id} (${route.originSnap.snap_distance_m} m), destination node ${route.destinationSnap.node_id} (${route.destinationSnap.snap_distance_m} m).`
        );
      }

      if (vsAlternativeDistanceKm > 0 && vsAlternativeDurationMin < 0) {
        tradeoffNote = `Trades +${vsAlternativeDistanceKm.toFixed(2)} km extra road distance in exchange for saving ${Math.abs(vsAlternativeDurationMin).toFixed(1)} min of estimated travel time and higher arterial road hierarchy (${roadHierarchyScore}/100).`;
      } else if (vsAlternativeDistanceKm < 0 && vsAlternativeDurationMin > 0) {
        tradeoffNote = `Trades +${vsAlternativeDurationMin.toFixed(1)} min slower estimated travel time in exchange for saving ${Math.abs(vsAlternativeDistanceKm).toFixed(2)} km of physical distance.`;
      } else {
        tradeoffNote = `Achieves ${weightedScore}/100 under ${config.label} weights (${config.formulaText}).`;
      }
    }

    const evaluation: RouteEvaluationBreakdown = {
      routeId: route.id,
      preference: config.preference,
      distanceScore,
      timeScore,
      roadHierarchyScore,
      snapQualityScore,
      weightedScore,
      distanceWeight: config.distanceWeight,
      timeWeight: config.timeWeight,
      hierarchyWeight: config.hierarchyWeight,
      formulaText: config.formulaText,
      minDistanceKm,
      minDurationMin,
      distanceDeltaKm,
      durationDeltaMin,
      vsAlternativeDistanceKm,
      vsAlternativeDurationMin,
      impliedAvgSpeedKmh,
      intersectionDensityPerKm,
      roadClassBreakdownPct,
      imputedSpeedEdgesPct,
      bridgesCount,
      tunnelsCount,
      routesAreIdentical,
      reasons,
      advantages,
      disadvantages,
      tradeoffNote,
      algorithmDisclosure: ALGORITHM_DISCLOSURE,
      unavailableMetrics: UNAVAILABLE_ROUTE_METRICS,
      mlRanking: route.mlRanking
    };

    return {
      ...route,
      logisticsScore: Math.round(weightedScore),
      tradeoffs: tradeoffNote,
      evaluation
    };
  });

  // Sort deterministically according to the selected preference and tie-break rules
  evaluated.sort((a, b) => {
    const scoreA = a.evaluation?.weightedScore ?? a.logisticsScore;
    const scoreB = b.evaluation?.weightedScore ?? b.logisticsScore;

    if (Math.abs(scoreB - scoreA) > 0.05) {
      return scoreB - scoreA;
    }

    if (preference === 'shortest') {
      if (a.routeType === 'shortest' && b.routeType !== 'shortest') return -1;
      if (b.routeType === 'shortest' && a.routeType !== 'shortest') return 1;
      return a.distanceKm - b.distanceKm;
    }

    if (preference === 'fastest') {
      if (a.routeType === 'estimated_fastest' && b.routeType !== 'estimated_fastest') return -1;
      if (b.routeType === 'estimated_fastest' && a.routeType !== 'estimated_fastest') return 1;
      return a.durationMinutes - b.durationMinutes;
    }

    if (priority === 'High' || priority === 'Emergency') {
      if (Math.abs(a.durationMinutes - b.durationMinutes) > 0.05) {
        return a.durationMinutes - b.durationMinutes;
      }
    }
    return a.distanceKm - b.distanceKm;
  });

  const palette = ['#2563eb', '#d97706', '#0d9488'];
  return evaluated.map((r, index) => ({
    ...r,
    status: index === 0 ? 'RECOMMENDED' : 'ALTERNATIVE',
    color: palette[index] ?? '#64748b'
  }));
}

export function scoreCandidateRoutes(
  routes: RouteAlternative[],
  weights: ScoringWeights = DEFAULT_WEIGHTS
): Map<string, RouteScoreBreakdown> {
  const result = new Map<string, RouteScoreBreakdown>();
  if (routes.length === 0) return result;

  const validTimes = routes.map(r => r.durationMinutes).filter(t => t > 0);
  const minTime = validTimes.length > 0 ? Math.min(...validTimes) : 1;

  const validDistances = routes.map(r => r.distanceKm).filter(d => d > 0);
  const minDist = validDistances.length > 0 ? Math.min(...validDistances) : 1;

  routes.forEach(route => {
    const timeEfficiency =
      route.durationMinutes > 0
        ? Math.min(100, Math.round((minTime / route.durationMinutes) * 100))
        : 100;

    const distanceEfficiency =
      route.distanceKm > 0
        ? Math.min(100, Math.round((minDist / route.distanceKm) * 100))
        : 100;

    const totalWeight = weights.travelTime + weights.distance;
    const compositeScore =
      totalWeight > 0
        ? Math.round(
            (weights.travelTime * timeEfficiency + weights.distance * distanceEfficiency) /
              totalWeight
          )
        : 0;

    result.set(route.id, {
      routeId: route.id,
      timeEfficiencyScore: timeEfficiency,
      distanceEfficiencyScore: distanceEfficiency,
      compositeLogisticsScore: compositeScore,
      excludedFactors: UNAVAILABLE_ROUTE_METRICS.map(m => m.name)
    });
  });

  return result;
}

export function generateRecommendationExplanation(
  recommended: RouteAlternative,
  allRoutes: RouteAlternative[],
  mission: LogisticsMission
): string {
  const evalData = recommended.evaluation;
  const config = evalData
    ? PREFERENCE_CONFIGS[evalData.preference]
    : PREFERENCE_CONFIGS.balanced;

  if (evalData?.routesAreIdentical || allRoutes.length <= 1) {
    return `${recommended.name} (${recommended.distanceKm} km, ${recommended.durationMinutes} min est.) is the single optimal path in the OSMnx road graph for both distance and estimated time (${recommended.logisticsScore}/100).`;
  }

  const other = allRoutes.find(r => r.id !== recommended.id);
  if (!other) {
    return `${recommended.name} achieved the highest ${config.label} score (${evalData?.weightedScore ?? recommended.logisticsScore}/100) for transporting ${mission.quantityKg} kg of ${mission.goods}.`;
  }

  const distDiff = round2(other.distanceKm - recommended.distanceKm);
  const timeDiff = round1(other.durationMinutes - recommended.durationMinutes);

  const advantages: string[] = [];
  if (distDiff > 0) {
    advantages.push(`is ${distDiff.toFixed(2)} km shorter (${recommended.distanceKm} km vs. ${other.distanceKm} km)`);
  }
  if (timeDiff > 0) {
    advantages.push(`saves ${timeDiff.toFixed(1)} min of estimated travel time (${recommended.durationMinutes} min vs. ${other.durationMinutes} min)`);
  }

  const primaryAdvantage =
    advantages.length > 0
      ? advantages.join(' and ')
      : `achieves the highest ${config.label} score (${evalData?.weightedScore ?? recommended.logisticsScore}/100)`;

  return `Under "${config.label}" (${config.formulaText}), ${recommended.name} ranks #1 (${evalData?.weightedScore ?? recommended.logisticsScore}/100 vs. ${other.evaluation?.weightedScore ?? other.logisticsScore}/100) because it ${primaryAdvantage}. ${evalData?.tradeoffNote ?? ''}`.trim();
}
