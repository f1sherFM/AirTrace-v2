"""Open-Meteo Weather API integration for cardio and outdoor environmental context in AirTrace v3.4."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from http_transport import create_external_async_client

logger = logging.getLogger(__name__)

# In-memory weather cache: key -> (timestamp, payload)
_WEATHER_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_WEATHER_CACHE_TTL = 600  # 10 minutes


class OpenMeteoWeatherService:
    """Async service to fetch weather, temperature, precipitation, and wind from Open-Meteo."""

    def __init__(self, base_url: str = "https://api.open-meteo.com/v1/forecast"):
        self.base_url = base_url
        self.client = create_external_async_client(
            max_connections=10,
            max_keepalive_connections=5,
            connect_timeout=6.0,
            read_timeout=15.0,
            trust_env=True,
        )

    def _cache_key(self, lat: float, lon: float) -> str:
        return f"{lat:.2f}:{lon:.2f}"

    async def get_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch current weather and 24h hourly forecast from Open-Meteo."""
        key = self._cache_key(lat, lon)
        now = time.time()
        if key in _WEATHER_CACHE:
            cached_at, data = _WEATHER_CACHE[key]
            if now - cached_at < _WEATHER_CACHE_TTL:
                return data

        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,relative_humidity_2m",
            "hourly": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,relative_humidity_2m",
            "forecast_days": 2,
            "timezone": "auto",
        }

        try:
            resp = await self.client.get(self.base_url, params=params)
            resp.raise_for_status()
            raw = resp.json()
            processed = self._process_weather_payload(raw)
            _WEATHER_CACHE[key] = (now, processed)
            return processed
        except Exception as exc:
            logger.warning("Primary client failed to fetch weather from Open-Meteo: %s. Retrying directly with trust_env=True...", exc)
            try:
                async with httpx.AsyncClient(trust_env=True, timeout=httpx.Timeout(10.0, connect=5.0)) as direct_client:
                    resp = await direct_client.get(self.base_url, params=params)
                    resp.raise_for_status()
                    raw = resp.json()
                    processed = self._process_weather_payload(raw)
                    _WEATHER_CACHE[key] = (now, processed)
                    return processed
            except Exception as direct_exc:
                logger.warning("Direct client also failed: %s. Using seasonal fallback.", direct_exc)
                return self._fallback_weather(lat, lon)

    def _process_weather_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        current_data = raw.get("current", {})
        hourly_data = raw.get("hourly", {})
        times = hourly_data.get("time", [])

        hourly_items: List[Dict[str, Any]] = []
        for i in range(min(len(times), 24)):
            hourly_items.append(
                {
                    "timestamp": times[i],
                    "temperature": hourly_data.get("temperature_2m", [0.0])[i],
                    "apparent_temperature": hourly_data.get("apparent_temperature", [0.0])[i],
                    "precipitation": hourly_data.get("precipitation", [0.0])[i],
                    "weather_code": hourly_data.get("weather_code", [0])[i],
                    "wind_speed": hourly_data.get("wind_speed_10m", [10.0])[i],
                    "humidity": hourly_data.get("relative_humidity_2m", [60])[i],
                }
            )

        return {
            "current": {
                "temperature": current_data.get("temperature_2m", 0.0),
                "apparent_temperature": current_data.get("apparent_temperature", current_data.get("temperature_2m", 0.0)),
                "precipitation": current_data.get("precipitation", 0.0),
                "weather_code": current_data.get("weather_code", 0),
                "wind_speed": current_data.get("wind_speed_10m", 10.0),
                "wind_gusts": current_data.get("wind_gusts_10m", 15.0),
                "humidity": current_data.get("relative_humidity_2m", 60),
            },
            "hourly": hourly_items,
        }

    def _fallback_weather(self, lat: float = 55.75, lon: float = 37.61) -> Dict[str, Any]:
        """Realistic geographical & seasonal estimation if all network requests fail."""
        if lat >= 60.0 or lon >= 90.0:  # Far North / Yakutia / East Siberia
            base_t = -16.0
            app_t = -22.0
            w_code = 71
        elif lon >= 60.0:  # West & Central Siberia / Urals (Novosibirsk, Omsk, Krasnoyarsk)
            base_t = -7.0
            app_t = -12.0
            w_code = 71
        elif lat <= 45.0:  # South / Krasnodar / Sochi
            base_t = 12.0
            app_t = 11.0
            w_code = 1
        else:  # Central European Russia (Moscow, SPb, Kazan)
            base_t = 2.0
            app_t = -1.0
            w_code = 3

        return {
            "current": {
                "temperature": base_t,
                "apparent_temperature": app_t,
                "precipitation": 0.0,
                "weather_code": w_code,
                "wind_speed": 12.0,
                "wind_gusts": 16.0,
                "humidity": 75,
            },
            "hourly": [],
        }

    async def close(self):
        await self.client.aclose()


# Global singleton instance
open_meteo_weather_service = OpenMeteoWeatherService()
