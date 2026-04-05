"""Compatibility facade for extracted domain logic and generic helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from domain.aqi.calculator import AQICalculator
from domain.nmu.detector import (
    NMUDetector,
    check_nmu_risk,
    get_nmu_recommendations,
    is_blacksky_conditions,
)
from domain.pollutants.aggregator import get_pollutant_name_russian
from core.validation import CoordinateValidator


try:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    MOSCOW_TZ = timezone(timedelta(hours=3), name="MSK")


def format_russian_timestamp(timestamp: datetime) -> str:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M МСК")


def validate_coordinates(lat: float, lon: float) -> bool:
    is_valid, _ = CoordinateValidator.validate_russian_territory(lat, lon)
    return is_valid
