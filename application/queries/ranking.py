"""Query service for Russian cities air quality ranking and analytics in AirTrace v3."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from application.queries.readonly import query_current_air_quality
from core.settings import load_cities_config

logger = logging.getLogger(__name__)

# In-memory snapshot cache for real measurements (key -> (timestamp, CityRankingItem))
_CITY_SNAPSHOTS_CACHE: dict[str, tuple[float, CityRankingItem]] = {}
SNAPSHOT_CACHE_TTL_SECONDS = 1800  # 30 minutes


def record_city_ranking_snapshot(
    key: str,
    name: str,
    lat: float,
    lon: float,
    aqi: int,
    aqi_category: str,
    aqi_color: str,
    region: Optional[str] = None,
    nmu_level: str = "none",
    pm2_5: Optional[float] = None,
) -> None:
    """Record a verified live measurement into the ranking cache."""
    item = CityRankingItem(
        key=key,
        name=name,
        region=region,
        lat=lat,
        lon=lon,
        aqi=aqi,
        aqi_category=aqi_category,
        aqi_color=aqi_color,
        nmu_level=nmu_level,
        pm2_5=pm2_5,
    )
    _CITY_SNAPSHOTS_CACHE[key] = (time.time(), item)


class CityRankingItem(BaseModel):
    key: str
    name: str
    region: Optional[str] = None
    lat: float
    lon: float
    aqi: int
    aqi_category: str
    aqi_color: str
    nmu_level: str
    dominant_pollutant: Optional[str] = None
    pm2_5: Optional[float] = None


class NationalOverviewResponse(BaseModel):
    timestamp: str
    cities_count: int
    average_aqi: float
    cleanest_cities: List[CityRankingItem] = Field(default_factory=list)
    attention_cities: List[CityRankingItem] = Field(default_factory=list)
    all_rankings: List[CityRankingItem] = Field(default_factory=list)
    summary: str


# Focused set of major industrial and geographic centers for quick live ranking
RANKING_CITY_KEYS = [
    "moscow", "spb", "novosibirsk", "ekaterinburg", "kazan",
    "nizhny", "chelyabinsk", "krasnoyarsk", "samara", "ufa",
    "rostov", "omsk", "krasnodar", "magnitogorsk", "surgut",
    "sochi", "vladivostok", "norilsk", "cherepovets", "irkutsk"
]


async def _fetch_city_ranking_item(key: str, city_cfg: Any) -> Optional[CityRankingItem]:
    # Check in-memory cache first
    now = time.time()
    if key in _CITY_SNAPSHOTS_CACHE:
        cached_ts, cached_item = _CITY_SNAPSHOTS_CACHE[key]
        if now - cached_ts < SNAPSHOT_CACHE_TTL_SECONDS:
            return cached_item

    try:
        data = await asyncio.wait_for(
            query_current_air_quality(lat=city_cfg.lat, lon=city_cfg.lon),
            timeout=4.0,
        )
        dominant = None
        if data.pollutants and data.pollutants.pm2_5 is not None:
            dominant = "PM2.5"
        elif data.pollutants and data.pollutants.no2 is not None:
            dominant = "NO2"

        item = CityRankingItem(
            key=key,
            name=city_cfg.name,
            region=city_cfg.region,
            lat=city_cfg.lat,
            lon=city_cfg.lon,
            aqi=data.aqi.value,
            aqi_category=data.aqi.category,
            aqi_color=data.aqi.color,
            nmu_level=getattr(data, "nmu_risk", None) or "none",
            dominant_pollutant=dominant,
            pm2_5=data.pollutants.pm2_5 if data.pollutants else None,
        )
        _CITY_SNAPSHOTS_CACHE[key] = (now, item)
        return item
    except Exception as exc:
        logger.debug("Ranking fetch skipped for %s: %s", key, exc)
        return None


async def query_national_ranking() -> NationalOverviewResponse:
    """Generate national overview ranking based on real measurements only."""
    config = load_cities_config()
    cities = config.cities

    now = time.time()
    items: list[CityRankingItem] = [
        item for key, (ts, item) in _CITY_SNAPSHOTS_CACHE.items()
        if now - ts < SNAPSHOT_CACHE_TTL_SECONDS and key in cities
    ]

    # If cache has few items, warm up a small priority slice of major cities
    if len(items) < 4:
        priority_keys = ["moscow", "spb", "kazan", "ekaterinburg", "chelyabinsk", "sochi"]
        uncached = [k for k in priority_keys if k not in _CITY_SNAPSHOTS_CACHE and k in cities]
        if uncached:
            tasks = [_fetch_city_ranking_item(k, cities[k]) for k in uncached]
            new_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in new_results:
                if isinstance(res, CityRankingItem) and res not in items:
                    items.append(res)

    if not items:
        return NationalOverviewResponse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            cities_count=0,
            average_aqi=0.0,
            summary="Рейтинг формируется по мере поступления замеров. Выберите интересующий город для анализа.",
        )

    # Sort all by AQI ascending (cleanest first)
    items.sort(key=lambda x: x.aqi)

    cleanest = items[:5]
    # Attention cities: highest AQI or having non-none NMU risk
    attention_candidates = sorted(
        items,
        key=lambda x: (x.nmu_level == "critical", x.nmu_level in ("high", "medium"), x.aqi),
        reverse=True,
    )
    attention = attention_candidates[:5]

    avg_aqi = round(sum(i.aqi for i in items) / len(items), 1)

    if avg_aqi <= 50:
        summary = f"В наблюдаемых городах РФ обстановка благоприятная (средний AQI: {avg_aqi})."
    elif avg_aqi <= 100:
        summary = f"Умеренный уровень загрязнения в наблюдаемых городах (средний AQI: {avg_aqi})."
    else:
        summary = f"Повышенный уровень загрязнения воздуха в ряде наблюдаемых городов (средний AQI: {avg_aqi})."

    return NationalOverviewResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        cities_count=len(items),
        average_aqi=avg_aqi,
        cleanest_cities=cleanest,
        attention_cities=attention,
        all_rankings=items,
        summary=summary,
    )
