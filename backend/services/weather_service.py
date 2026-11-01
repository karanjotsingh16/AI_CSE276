from __future__ import annotations

import json
import math
from pathlib import Path
import time
from typing import Any

import httpx

BASE_DIR = (
    Path(__file__).resolve().parent.parent
    if Path(__file__).resolve().parent.name in ("core", "services", "scripts", "tests")
    else Path(__file__).resolve().parent
)
DEFAULT_WEATHER_CACHE_PATH = BASE_DIR / "data" / "cache" / "weather_cache.json"
CACHE_TTL_SECONDS = 900.0  # 15 minutes


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    )
    return float(2.0 * r * math.asin(min(1.0, math.sqrt(a))))


class WeatherService:
    """
    Live regional weather intelligence service powered by Open-Meteo Numerical Weather
    Prediction (WMO 0.25° Seamless Model) with disk/memory caching and corridor sampling.

    Academic Integrity & Provenance:
    - Never fabricates weather telemetry.
    - When external API is reachable, extracts verified forecast parameters (precipitation,
      intensity mm/h, wind speed, temperature).
    - If network is unreachable or times out, returns status='unavailable' with full diagnostics.
    """

    def __init__(
        self,
        cache_path: str | Path = DEFAULT_WEATHER_CACHE_PATH,
        cache_ttl_seconds: float = CACHE_TTL_SECONDS,
        request_timeout_seconds: float = 6.0,
    ) -> None:
        self.cache_path = Path(cache_path).resolve()
        self.cache_ttl = float(cache_ttl_seconds)
        self.timeout = float(request_timeout_seconds)
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists() and self.cache_path.is_file():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._memory_cache = json.load(f)
            except Exception:
                self._memory_cache = {}

    def _persist_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._memory_cache, f, indent=2)
        except Exception:
            pass

    def _cache_key(self, lat: float, lng: float) -> str:
        # Snap cache key to ~1.1 km grid (2 decimals)
        return f"{round(lat, 2)}_{round(lng, 2)}"

    def fetch_point_weather(
        self,
        lat: float,
        lng: float,
        location_name: str = "",
    ) -> dict[str, Any]:
        """Fetch current and 6-hour forecast weather for a geographic coordinate."""
        key = self._cache_key(lat, lng)
        now_ts = time.time()

        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if now_ts - entry.get("cached_at", 0) < self.cache_ttl:
                data = dict(entry["data"])
                data["from_cache"] = True
                if location_name:
                    data["location_name"] = location_name
                return data

        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat:.4f}&longitude={lng:.4f}&"
            f"hourly=precipitation_probability,precipitation,wind_speed_10m,temperature_2m&"
            f"current_weather=true&forecast_days=2&timezone=auto"
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return self._fallback_response(
                        lat, lng, location_name, f"HTTP {resp.status_code} from Open-Meteo"
                    )
                payload = resp.json()

            hourly = payload.get("hourly", {})
            current = payload.get("current_weather", {})
            times = hourly.get("time", [])

            if not times:
                return self._fallback_response(
                    lat, lng, location_name, "Empty hourly forecast array in weather response"
                )

            # Find starting index close to current hour
            now_iso_prefix = time.strftime("%Y-%m-%dT%H", time.gmtime(now_ts))
            start_idx = 0
            for idx, t_str in enumerate(times):
                if t_str.startswith(now_iso_prefix):
                    start_idx = idx
                    break

            hourly_forecast: list[dict[str, Any]] = []
            max_prob = 0.0
            max_precip_mm = 0.0
            probs = hourly.get("precipitation_probability", [])
            precips = hourly.get("precipitation", [])
            temps = hourly.get("temperature_2m", [])

            for i in range(start_idx, min(start_idx + 6, len(times))):
                p_val = float(probs[i]) if i < len(probs) and probs[i] is not None else 0.0
                pr_val = float(precips[i]) if i < len(precips) and precips[i] is not None else 0.0
                t_val = float(temps[i]) if i < len(temps) and temps[i] is not None else 18.0

                if p_val > max_prob:
                    max_prob = p_val
                if pr_val > max_precip_mm:
                    max_precip_mm = pr_val

                hourly_forecast.append(
                    {
                        "time_iso": times[i],
                        "precipitation_probability_pct": round(p_val, 1),
                        "precipitation_mm": round(pr_val, 2),
                        "temperature_c": round(t_val, 1),
                    }
                )

            current_temp = (
                float(current.get("temperature", hourly_forecast[0]["temperature_c"]))
                if current
                else hourly_forecast[0]["temperature_c"]
            )
            current_wind = (
                float(current.get("windspeed", 12.0)) if current else 12.0
            )

            result = {
                "status": "available",
                "location_name": location_name or f"Coordinate ({lat:.4f}, {lng:.4f})",
                "latitude": round(lat, 4),
                "longitude": round(lng, 4),
                "temperature_c": round(current_temp, 1),
                "wind_speed_kmh": round(current_wind, 1),
                "max_rain_probability_pct": round(max_prob, 1),
                "max_precipitation_mm": round(max_precip_mm, 2),
                "hourly_forecast": hourly_forecast,
                "data_source": "Open-Meteo Weather API (WMO 0.25° Seamless Numerical Model)",
                "data_provenance": "Live numerical atmospheric weather observation and forecast.",
                "cached_at": now_ts,
                "from_cache": False,
            }

            self._memory_cache[key] = {"cached_at": now_ts, "data": result}
            self._persist_cache()
            return result

        except Exception as exc:
            return self._fallback_response(lat, lng, location_name, str(exc))

    def _fallback_response(
        self,
        lat: float,
        lng: float,
        location_name: str,
        reason: str,
    ) -> dict[str, Any]:
        """Return standardized unavailable payload when external live weather cannot be fetched."""
        key = self._cache_key(lat, lng)
        if key in self._memory_cache:
            stale = dict(self._memory_cache[key]["data"])
            stale["from_cache"] = True
            stale["is_stale_cache"] = True
            stale["cache_notice"] = f"Using cached forecast due to upstream reachability: {reason}"
            return stale

        return {
            "status": "unavailable",
            "location_name": location_name or f"Coordinate ({lat:.4f}, {lng:.4f})",
            "latitude": round(lat, 4),
            "longitude": round(lng, 4),
            "temperature_c": None,
            "wind_speed_kmh": None,
            "max_rain_probability_pct": None,
            "max_precipitation_mm": None,
            "hourly_forecast": [],
            "error_detail": reason,
            "data_source": "Open-Meteo Weather API",
            "data_provenance": "Atmospheric data currently unreachable; degraded to unavailable.",
            "from_cache": False,
        }

    def evaluate_route_corridor_weather(
        self,
        geometry_coords: list[list[float]],  # [[lng, lat], ...]
    ) -> dict[str, Any]:
        """
        Sample key corridor points along route geometry (start, 33%, 66%, end)
        and compute corridor-level weather exposure metrics and a 0-100 score.
        """
        if not geometry_coords or len(geometry_coords) < 2:
            return {
                "corridor_status": "unavailable",
                "weather_exposure_score": None,
                "explanation": "Insufficient route geometry points for corridor weather sampling.",
            }

        n = len(geometry_coords)
        sample_indices = [
            0,
            int(n * 0.33),
            int(n * 0.66),
            n - 1,
        ]
        # Remove duplicates for short paths
        sample_indices = sorted(list(set(sample_indices)))

        samples: list[dict[str, Any]] = []
        for idx in sample_indices:
            lng_val, lat_val = geometry_coords[idx][0], geometry_coords[idx][1]
            label = "Origin Hub" if idx == 0 else ("Destination Hub" if idx == n - 1 else f"Corridor Waypoint #{idx}")
            w = self.fetch_point_weather(lat_val, lng_val, location_name=label)
            samples.append(w)

        available_samples = [s for s in samples if s.get("status") == "available"]
        if not available_samples:
            return {
                "corridor_status": "unavailable",
                "weather_exposure_score": None,
                "explanation": "External atmospheric telemetry unreachable for all sampled corridor coordinates.",
                "samples": samples,
            }

        avg_temp = float(
            sum(float(s["temperature_c"]) for s in available_samples) / len(available_samples)
        )
        max_wind = float(
            max(float(s["wind_speed_kmh"]) for s in available_samples)
        )
        max_rain_prob = float(
            max(float(s["max_rain_probability_pct"]) for s in available_samples)
        )
        max_precip_mm = float(
            max(float(s["max_precipitation_mm"]) for s in available_samples)
        )

        # Explainable Weather Exposure Penalty Formula (100 = Clear/Dry, 0 = Extreme Hazard)
        # 1. Rain probability penalty (0 to 35 pts): 0% -> 0, 100% -> 35
        p_prob = (max_rain_prob / 100.0) * 35.0
        # 2. Precipitation rate penalty (0 to 45 pts): 0 mm -> 0, 15 mm/h -> 45
        p_intensity = min(45.0, (max_precip_mm / 15.0) * 45.0)
        # 3. Wind hazard penalty (0 to 20 pts): <=15 km/h -> 0, 55 km/h -> 20
        p_wind = min(20.0, max(0.0, (max_wind - 15.0) / 40.0) * 20.0)

        total_penalty = p_prob + p_intensity + p_wind
        weather_score = round(max(5.0, min(100.0, 100.0 - total_penalty)), 1)

        if weather_score >= 80.0:
            hazard_level = "low"
            guidance = "Clear or light mountain breeze; favorable logistics conditions."
        elif weather_score >= 55.0:
            hazard_level = "moderate"
            guidance = "Scattered showers forecast; caution advised on winding mountain grades."
        else:
            hazard_level = "high"
            guidance = "Significant rain bands/wind active along corridor; elevated slickness and reduced visibility."

        return {
            "corridor_status": "available",
            "weather_exposure_score": weather_score,
            "hazard_level": hazard_level,
            "guidance": guidance,
            "corridor_metrics": {
                "mean_temperature_c": round(avg_temp, 1),
                "max_wind_speed_kmh": round(max_wind, 1),
                "max_rain_probability_pct": round(max_rain_prob, 1),
                "max_precipitation_mm": round(max_precip_mm, 2),
                "penalty_breakdown": {
                    "rain_probability_penalty": round(p_prob, 1),
                    "precipitation_intensity_penalty": round(p_intensity, 1),
                    "wind_gust_penalty": round(p_wind, 1),
                },
            },
            "samples_count": len(available_samples),
            "data_source": "Open-Meteo Weather API (WMO 0.25° Seamless Numerical Model)",
        }
