"""Query handlers for outdoor cardio and running analytics in AirTrace v3.4."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from core.settings import get_cities_mapping
from domain.cardio import (
    CardioAnalysisReport,
    analyze_city_cardio,
)
from infrastructure.integrations.open_meteo_weather import open_meteo_weather_service
from application.queries.readonly import (
    query_current_air_quality,
    query_forecast_air_quality,
)

logger = logging.getLogger(__name__)


async def get_city_cardio_analysis(city_key: str) -> CardioAnalysisReport:
    """Fetch air and weather telemetry, then build comprehensive CardioAnalysisReport."""
    cities = get_cities_mapping()
    norm_key = city_key.strip().lower()
    if norm_key not in cities:
        raise KeyError(f"City '{city_key}' not found in catalog")

    city = cities[norm_key]
    lat = float(city["lat"])
    lon = float(city["lon"])
    city_name = city["name"]
    region = city.get("region")

    # Fetch air quality, air forecast, and weather telemetry concurrently
    current_air_res, forecast_air_res, weather_res = await asyncio.gather(
        query_current_air_quality(lat=lat, lon=lon),
        query_forecast_air_quality(lat=lat, lon=lon, hours=24),
        open_meteo_weather_service.get_weather(lat=lat, lon=lon),
        return_exceptions=True,
    )

    # 1. Handle current air quality
    current_aqi = 35
    pollutants: Dict[str, Any] = {}
    nmu_active = False
    if not isinstance(current_air_res, Exception) and current_air_res is not None:
        try:
            air_dump = current_air_res.model_dump(mode="json")
            aqi_obj = air_dump.get("aqi", {})
            current_aqi = int(aqi_obj.get("value", 35))
            pollutants = air_dump.get("pollutants", {})
            nmu_risk = air_dump.get("nmu_risk")
            if nmu_risk and str(nmu_risk).lower() in ("high", "alert", "critical", "active"):
                nmu_active = True
        except Exception as exc:
            logger.debug("Failed to extract air metrics for %s: %s", city_key, exc)

    # 2. Handle weather
    weather_data: Dict[str, Any] = {}
    weather_hourly: List[Dict[str, Any]] = []
    if not isinstance(weather_res, Exception) and isinstance(weather_res, dict):
        weather_data = weather_res.get("current", {})
        weather_hourly = weather_res.get("hourly", [])
    else:
        weather_data = {
            "temperature": 5.0,
            "apparent_temperature": 4.0,
            "precipitation": 0.0,
            "weather_code": 0,
            "wind_speed": 10.0,
            "wind_gusts": 15.0,
        }

    # 3. Synchronize hourly forecast combining air + weather
    hourly_forecast: List[Dict[str, Any]] = []
    air_items: List[Dict[str, Any]] = []
    if not isinstance(forecast_air_res, Exception) and isinstance(forecast_air_res, list):
        for item in forecast_air_res:
            try:
                air_items.append(item.model_dump(mode="json"))
            except Exception:
                pass

    limit_hours = min(24, max(len(air_items), len(weather_hourly)))
    for i in range(limit_hours):
        air_item = air_items[i] if i < len(air_items) else {}
        weath_item = weather_hourly[i] if i < len(weather_hourly) else {}

        ts = air_item.get("timestamp") or weath_item.get("timestamp") or f"{i:02d}:00"
        h_aqi = air_item.get("aqi", {}).get("value", current_aqi) if isinstance(air_item.get("aqi"), dict) else current_aqi
        h_temp = weath_item.get("temperature", weather_data.get("temperature", 5.0))
        h_app_temp = weath_item.get("apparent_temperature", h_temp)
        h_precip = weath_item.get("precipitation", 0.0)
        h_wcode = weath_item.get("weather_code", 0)
        h_wind = weath_item.get("wind_speed", weather_data.get("wind_speed", 10.0))

        hourly_forecast.append(
            {
                "timestamp": str(ts),
                "aqi": int(h_aqi),
                "temperature": float(h_temp),
                "apparent_temperature": float(h_app_temp),
                "precipitation": float(h_precip),
                "weather_code": int(h_wcode),
                "wind_speed": float(h_wind),
            }
        )

    # 4. Generate domain analysis report
    report = analyze_city_cardio(
        city_key=norm_key,
        city_name=city_name,
        region=region,
        current_aqi=current_aqi,
        pollutants=pollutants,
        weather_data=weather_data,
        hourly_forecast=hourly_forecast,
        nmu_active=nmu_active,
    )

    return report
