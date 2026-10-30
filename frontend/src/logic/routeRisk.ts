import { RouteAlternative } from '../types/route';
import { DisasterAlert } from '../types/alert';
import { WeatherData } from '../types/weather';

export interface RouteSafetyAssessment {
  overallRiskScore: number | null; // 0-100, or null if insufficient data
  classification: 'LOW' | 'MODERATE' | 'HIGH' | 'UNAVAILABLE';
  classificationLabel: string;
  explanation: string;
  activeCorridorAlerts: DisasterAlert[];
  weatherHazardFactor: number | null;
  terrainFactor: number | null;
  dataLimitations: string[];
}

export function assessRouteSafety(
  route: RouteAlternative | null,
  alerts: DisasterAlert[],
  weather: WeatherData
): RouteSafetyAssessment {
  if (!route) {
    return {
      overallRiskScore: null,
      classification: 'UNAVAILABLE',
      classificationLabel: 'UNAVAILABLE',
      explanation: 'No route selected for safety evaluation.',
      activeCorridorAlerts: [],
      weatherHazardFactor: null,
      terrainFactor: null,
      dataLimitations: ['No active route geometry selected']
    };
  }

  const limitations: string[] = [];

  // 1. Alert factor
  const corridorAlerts = alerts.filter(a => a.intersectsRoute !== false);
  const severeAlerts = corridorAlerts.filter(a => a.severity === 'Severe' || a.severity === 'Warning');

  // Check if alert source had errors
  if (alerts.length === 0) {
    limitations.push('Government CAP alert spatial verification feed is operating in regional cache mode.');
  }

  // 2. Weather factor
  const weatherRisk = weather.weatherRiskScore;
  if (weatherRisk === null) {
    limitations.push('Real-time weather observation metrics could not be confirmed for this corridor.');
  }

  // 3. Terrain factor
  const terrainScore = route.terrainExposureScore;
  if (terrainScore == null) {
    limitations.push('Copernicus DEM slope gradient profile is unverified for this segment.');
  }

  // Check if critical inputs are missing
  if (weatherRisk === null && alerts.length === 0) {
    return {
      overallRiskScore: null,
      classification: 'UNAVAILABLE',
      classificationLabel: 'UNAVAILABLE',
      explanation: 'Risk classification is incomplete because current official alert and live weather data could not be verified.',
      activeCorridorAlerts: corridorAlerts,
      weatherHazardFactor: null,
      terrainFactor: terrainScore ?? null,
      dataLimitations: limitations
    };
  }

  // Calculate composite hazard score (0-100)
  // Base disaster score: 40%
  // Weather hazard: 35%
  // Terrain slope: 25%
  let disasterWeight = 0.40;
  let weatherWeight = 0.35;
  let terrainWeight = 0.25;

  let totalHazard = (route.disasterRiskScore * disasterWeight) + 
                    ((weatherRisk ?? route.weatherRiskScore) * weatherWeight) + 
                    (terrainScore * terrainWeight);

  // If there are confirmed severe alerts intersecting the route, elevate hazard
  if (severeAlerts.length > 0) {
    totalHazard = Math.max(totalHazard, 75);
    limitations.push(`Contains ${severeAlerts.length} active high-severity hazard warning(s) directly along corridor.`);
  }

  const score = Math.round(Math.min(100, Math.max(0, totalHazard)));

  let classification: 'LOW' | 'MODERATE' | 'HIGH' | 'UNAVAILABLE' = 'LOW';
  let classificationLabel = 'LOW RISK';
  let explanation = '';

  if (score >= 65) {
    classification = 'HIGH';
    classificationLabel = 'HIGH RISK';
    explanation = 'Modelled high hazard: Elevated likelihood of mountain slope instability, surface runoff, or road impediment along this corridor.';
  } else if (score >= 35) {
    classification = 'MODERATE';
    classificationLabel = 'MODERATE RISK';
    explanation = 'Modelled moderate caution: Localized terrain exposure and adverse atmospheric factors warrant reduced convoy speed and driver vigilance.';
  } else {
    classification = 'LOW';
    classificationLabel = 'LOW RISK';
    explanation = 'Modelled low risk: No active severe warnings detected and current atmospheric/terrain indices remain within standard operational tolerances.';
  }

  return {
    overallRiskScore: score,
    classification,
    classificationLabel,
    explanation,
    activeCorridorAlerts: corridorAlerts,
    weatherHazardFactor: weatherRisk ?? route.weatherRiskScore,
    terrainFactor: terrainScore,
    dataLimitations: limitations
  };
}
