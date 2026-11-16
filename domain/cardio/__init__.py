"""Cardio, running, and outdoor activity domain module for AirTrace v3.4."""

from .models import (
    ActivityLevel,
    CardioAnalysisReport,
    CardioHourScore,
    CardioRecommendation,
    PrecipitationType,
    SurfaceCondition,
    ThermalZone,
)
from .calculator import (
    analyze_city_cardio,
    calculate_run_score,
    determine_surface_condition,
    determine_thermal_zone,
    generate_activity_recommendations,
)

__all__ = [
    "ActivityLevel",
    "ThermalZone",
    "SurfaceCondition",
    "PrecipitationType",
    "CardioRecommendation",
    "CardioHourScore",
    "CardioAnalysisReport",
    "calculate_run_score",
    "determine_thermal_zone",
    "determine_surface_condition",
    "generate_activity_recommendations",
    "analyze_city_cardio",
]
