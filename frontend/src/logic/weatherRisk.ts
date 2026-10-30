import { RiskClassification } from '../types/weather';

export interface WeatherMetricsInput {
  rainProbMax: number | null; // 0-100%
  windSpeedKmh: number | null; // km/h
  precipitationMmMax: number | null; // mm
}

/**
 * Calculates a 0-100 modelled weather hazard score based on forecast precipitation probability,
 * precipitation accumulation rate, and wind speed.
 * 
 * Weights:
 * - Rain probability (40%): 0-100% maps directly
 * - Rain intensity (35%): >20mm/hr is severe monsoon cloudburst
 * - Wind speed (25%): >50km/h is hazardous in mountain terrain
 */
export function calculateWeatherRiskScore(metrics: WeatherMetricsInput): {
  score: number | null;
  classification: RiskClassification;
  explanation: string;
} {
  if (metrics.rainProbMax === null && metrics.windSpeedKmh === null) {
    return {
      score: null,
      classification: 'UNAVAILABLE',
      explanation: 'Weather risk cannot be computed: Live atmospheric observation data unavailable.'
    };
  }

  const rainProb = metrics.rainProbMax ?? 0;
  const precipRate = metrics.precipitationMmMax ?? 0;
  const wind = metrics.windSpeedKmh ?? 0;

  // Rain probability component (0 - 40 pts)
  const probComponent = (rainProb / 100) * 40;

  // Rain intensity component (0 - 35 pts)
  // 0mm = 0, 5mm = 15, 15mm = 30, >25mm = 35
  const intensityComponent = Math.min(35, (precipRate / 20) * 35);

  // Wind component (0 - 25 pts)
  // <15 km/h = mild, 35 km/h = moderate, >60 km/h = severe
  const windComponent = Math.min(25, (wind / 55) * 25);

  const rawScore = Math.round(probComponent + intensityComponent + windComponent);
  const score = Math.max(0, Math.min(100, rawScore));

  let classification: RiskClassification = 'LOW';
  let explanation = 'Mild atmospheric conditions with minimal disruption expected on logistics roads.';

  if (score >= 70) {
    classification = 'SEVERE';
    explanation = 'Severe weather hazard: Heavy precipitation and gusts elevated risk of flash flooding and road slicks.';
  } else if (score >= 45) {
    classification = 'HIGH';
    explanation = 'Elevated weather risk: Rain bands active across the corridor; reduced mountain visibility and slippery grades.';
  } else if (score >= 25) {
    classification = 'MODERATE';
    explanation = 'Moderate weather caution: Light-to-moderate showers forecast; mountain fog likely in passes.';
  } else {
    classification = 'LOW';
    explanation = 'Favorable weather conditions: Dry or light breeze along the majority of the mountain corridor.';
  }

  return { score, classification, explanation };
}
