"""Schemas for AirTrace v3 API."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field

from domain.advisory.models import OverallAdvisory
from schemas import AirQualityData, LocationInfo, AQIInfo, PollutantData, WeatherInfo, ResponseMetadata


class AirQualityDataV3(AirQualityData):
    """Enriched v3 Air Quality Data with life-style advisory and city context."""
    city_name: Optional[str] = Field(None, description="Человекочитаемое название города")
    region: Optional[str] = Field(None, description="Регион / субъект РФ")
    advisory: Optional[OverallAdvisory] = Field(None, description="Рекомендации по активностям и здоровью")
    api_version: str = Field(default="3.0", description="Версия контракта API")


class ForecastSummary(BaseModel):
    hours: int
    peak_aqi: int
    peak_hour: str
    peak_category: str
    average_aqi: float
    safest_hour: str
    trend: str


class ForecastResponseV3(BaseModel):
    location: LocationInfo
    city_name: Optional[str] = None
    generated_at: str
    summary: ForecastSummary
    items: List[AirQualityData]
