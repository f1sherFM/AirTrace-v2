"""AirTrace v3 Public API Routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.v3.schemas import AirQualityDataV3, ForecastResponseV3, ForecastSummary
from application.queries.cities import CitySearchResponse, search_cities
from application.queries.health import query_health, query_liveness, query_readiness
from application.queries.ranking import NationalOverviewResponse, query_national_ranking
from application.queries.readonly import (
    query_current_air_quality,
    query_forecast_air_quality,
)
from application.queries.v2_readonly import (
    query_history_v2,
    query_trends_v2,
)
from core.settings import load_cities_config
from domain.advisory import generate_activity_advisories, OverallAdvisory
from domain.cardio import CardioAnalysisReport
from application.queries.cardio import get_city_cardio_analysis
from schemas import (
    ErrorResponse,
    HealthCheckResponse,
    HistoryQueryResponse,
    HistoryRange,
    HistorySortOrder,
    HistoryTrendResponse,
    TrendRange,
)

router = APIRouter(prefix="/v3", tags=["AirTrace v3"])

V3_RESPONSE_HEADERS = {
    "X-AirTrace-API-Version": "3",
    "X-AirTrace-Contract": "v3-public",
}

V3_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _resolve_coordinates(
    *,
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> tuple[float, float, Optional[str], Optional[str]]:
    """Resolves coordinates from either city key or lat/lon pair."""
    config = load_cities_config()
    cities = config.cities

    if city:
        norm_key = city.strip().lower()
        if norm_key not in cities:
            raise HTTPException(status_code=404, detail=f"City '{city}' not found in configuration")
        city_cfg = cities[norm_key]
        return city_cfg.lat, city_cfg.lon, city_cfg.name, city_cfg.region

    if lat is not None and lon is not None:
        return lat, lon, None, None

    raise HTTPException(
        status_code=400,
        detail="Please provide either 'city' parameter or both 'lat' and 'lon'",
    )


@router.get("/cities", response_model=CitySearchResponse, responses=V3_ERROR_RESPONSES)
async def get_cities_v3(
    q: Optional[str] = Query(None, description="Поисковый запрос (название, транслит или регион)"),
    limit: int = Query(100, ge=1, le=100, description="Максимальное количество результатов"),
):
    """Поиск и получение каталога городов России (75+ городов с координатами и регионами)."""
    return search_cities(query=q, limit=limit)


@router.get("/cities/ranking", response_model=NationalOverviewResponse, responses=V3_ERROR_RESPONSES)
async def get_national_ranking_v3():
    """Национальный рейтинг качества воздуха в городах России: чистейшие города, зоны внимания и сводка."""
    return await query_national_ranking()


@router.get("/activities/advice", response_model=OverallAdvisory, responses=V3_ERROR_RESPONSES)
async def get_activity_advice_v3(
    city: Optional[str] = Query(None, description="Код города (например, moscow, kazan, krasnoyarsk)"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Широта"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Долгота"),
):
    """Получение персонализированных рекомендаций по активности (спорт, проветривание, маски, очистители)."""
    target_lat, target_lon, _, _ = _resolve_coordinates(city=city, lat=lat, lon=lon)
    air_data = await query_current_air_quality(lat=target_lat, lon=target_lon)

    nmu_risk = getattr(air_data, "nmu_risk", None) or "none"
    pollutants_dict = air_data.pollutants.model_dump() if air_data.pollutants else {}
    weather_dict = air_data.weather.model_dump() if air_data.weather else {}

    return generate_activity_advisories(
        aqi_value=air_data.aqi.value,
        aqi_category=air_data.aqi.category,
        nmu_level=nmu_risk,
        pollutants=pollutants_dict,
        weather=weather_dict,
    )


@router.get("/cardio/{city}", response_model=CardioAnalysisReport, responses=V3_ERROR_RESPONSES)
async def get_city_cardio_v3(
    city: str,
):
    """Детальный аналитический отчет для ходьбы и бега с учетом качества воздуха, сезона, мороза и осадков."""
    try:
        return await get_city_cardio_analysis(city)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Город '{city}' не найден в каталоге")


@router.get("/current", response_model=AirQualityDataV3, responses=V3_ERROR_RESPONSES)
async def get_current_air_quality_v3(
    city: Optional[str] = Query(None, description="Код города (например, moscow, kazan, spb)"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Широта"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Долгота"),
):
    """Текущее качество воздуха с включенными рекомендациями по активности и региональным контекстом."""
    target_lat, target_lon, city_name, region = _resolve_coordinates(city=city, lat=lat, lon=lon)

    base_data = await query_current_air_quality(lat=target_lat, lon=target_lon)
    nmu_risk = getattr(base_data, "nmu_risk", None) or "none"

    advisories = generate_activity_advisories(
        aqi_value=base_data.aqi.value,
        aqi_category=base_data.aqi.category,
        nmu_level=nmu_risk,
        pollutants=base_data.pollutants.model_dump() if base_data.pollutants else {},
        weather=base_data.weather.model_dump() if base_data.weather else {},
    )

    data_dict = base_data.model_dump()
    data_dict["city_name"] = city_name or (base_data.weather.location_name if base_data.weather else None)
    data_dict["region"] = region
    data_dict["advisory"] = advisories
    data_dict["api_version"] = "3.0"

    return AirQualityDataV3(**data_dict)


@router.get("/forecast", response_model=ForecastResponseV3, responses=V3_ERROR_RESPONSES)
async def get_forecast_air_quality_v3(
    city: Optional[str] = Query(None, description="Код города"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Широта"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Долгота"),
    hours: int = Query(24, ge=1, le=168, description="Горизонт прогноза в часах"),
):
    """Почасовой прогноз качества воздуха с автоматическим расчетом пиков загрязнения и безопасных окон."""
    target_lat, target_lon, city_name, _ = _resolve_coordinates(city=city, lat=lat, lon=lon)
    items = await query_forecast_air_quality(lat=target_lat, lon=target_lon, hours=hours)

    if not items:
        raise HTTPException(status_code=503, detail="Forecast data unavailable")

    peak_item = max(items, key=lambda x: x.aqi.value)
    min_item = min(items, key=lambda x: x.aqi.value)
    avg_val = round(sum(x.aqi.value for x in items) / len(items), 1)

    delta = items[-1].aqi.value - items[0].aqi.value
    if delta >= 10:
        trend_desc = "Ухудшение к концу периода"
    elif delta <= -10:
        trend_desc = "Улучшение к концу периода"
    else:
        trend_desc = "Стабильное состояние"

    summary = ForecastSummary(
        hours=len(items),
        peak_aqi=peak_item.aqi.value,
        peak_hour=peak_item.timestamp.isoformat() if hasattr(peak_item.timestamp, "isoformat") else str(peak_item.timestamp),
        peak_category=peak_item.aqi.category,
        average_aqi=avg_val,
        safest_hour=min_item.timestamp.isoformat() if hasattr(min_item.timestamp, "isoformat") else str(min_item.timestamp),
        trend=trend_desc,
    )

    return ForecastResponseV3(
        location=items[0].location,
        city_name=city_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        items=items,
    )


@router.get("/history", response_model=HistoryQueryResponse, responses=V3_ERROR_RESPONSES)
async def get_history_v3(
    range: HistoryRange = Query(HistoryRange.LAST_24H, description="Диапазон истории: 24h, 7d, 30d"),
    page: int = Query(1, ge=1, description="Страница"),
    page_size: int = Query(50, ge=1, le=500, description="Количество записей"),
    sort: HistorySortOrder = Query(HistorySortOrder.DESC, description="Сортировка: desc или asc"),
    city: Optional[str] = Query(None, description="Код города"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Широта"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Долгота"),
):
    """Исторические данные качества воздуха с поддержкой поиска по городам и координатам."""
    return await query_history_v2(
        range_value=range,
        page=page,
        page_size=page_size,
        sort=sort,
        city=city,
        lat=lat,
        lon=lon,
    )


@router.get("/trends", response_model=HistoryTrendResponse, responses=V3_ERROR_RESPONSES)
async def get_trends_v3(
    range: TrendRange = Query(TrendRange.LAST_7D, description="Диапазон тренда: 7d или 30d"),
    city: Optional[str] = Query(None, description="Код города"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Широта"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Долгота"),
):
    """Агрегированные тренды качества воздуха с индикацией направления динамики."""
    return await query_trends_v2(range_value=range, city=city, lat=lat, lon=lon)


@router.get("/health", response_model=HealthCheckResponse, responses=V3_ERROR_RESPONSES)
async def get_health_v3():
    """Проверка состояния системы и компонентов в контракте v3."""
    return await query_health()
