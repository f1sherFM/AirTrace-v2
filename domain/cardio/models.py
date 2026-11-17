"""Pydantic models for outdoor cardio, running, and walking analytics in AirTrace v3.4."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ActivityLevel(str, Enum):
    """Intensity level of outdoor physical activity."""
    WALKING = "walking"        # Ходьба, прогулки (12-18 л/мин)
    JOGGING = "jogging"        # Оздоровительный бег / джоггинг (40-60 л/мин)
    TEMPO_RUN = "tempo_run"    # Темповый бег / интервалы / марафон (90-120+ л/мин)


class ThermalZone(str, Enum):
    """Thermal comfort and cold-tolerance zone with Siberian calibration."""
    HEAT = "heat"                     # > +24°C: жара, риск перегрева и озона
    WARM = "warm"                     # +15°C .. +24°C: тепло, легко
    COOL_OPTIMAL = "cool_optimal"     # +5°C .. +14°C: золотой стандарт для бега
    MILD_CHILL = "mild_chill"         # 0°C .. +4°C: сырая прохлада
    MILD_WINTER = "mild_winter"       # -1°C .. -14°C: бодрая рабочая зима
    DEEP_FREEZE = "deep_freeze"       # -15°C .. -23°C: крепкий сибирский мороз (терпимо)
    EXTREME_FREEZE = "extreme_freeze" # <= -24°C: экстремальный мороз (стоп-сигнал для бега)


class SurfaceCondition(str, Enum):
    """Condition of running and walking surface based on weather and precipitation."""
    DRY = "dry"                       # Сухо, идеальное сцепление
    DAMP = "damp"                     # Влажно, допустимо
    WET = "wet"                       # Мокро, лужи, риск промокания
    SLUSH = "slush"                   # Слякоть / каша из снега и реагентов
    ICE = "ice"                       # Гололедица / ледяной дождь (высокий риск травм)
    COMPACT_SNOW = "compact_snow"     # Укатанный сухой снег (комфортно в трейлах)


class PrecipitationType(str, Enum):
    """Categorized precipitation type."""
    NONE = "none"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    FREEZING_RAIN = "freezing_rain"
    SNOW = "snow"
    BLIZZARD = "blizzard"


class CardioRecommendation(BaseModel):
    """Detailed recommendation tailored to a specific physical activity level."""
    activity: ActivityLevel
    status: str                       # "optimal", "good", "caution", "danger"
    status_label: str                 # "Отлично", "Хорошо", "С осторожностью", "Не рекомендуется"
    badge_color: str                  # Hex color code (#10b981, #f59e0b, #ef4444, etc.)
    headline: str
    description: str
    max_duration_minutes: Optional[int] = None
    gear_tips: List[str] = Field(default_factory=list)
    breathing_tips: List[str] = Field(default_factory=list)
    pulse_drift_bpm: int = 0          # Expected heart rate spike due to air/weather stress


class CardioHourScore(BaseModel):
    """Hourly running & walking suitability score for 24-hour timeline."""
    timestamp: str
    hour_label: str                   # "08:00"
    run_score: int                    # 0..100
    air_score: int                    # 0..100
    weather_score: int                # 0..100
    aqi: int
    temperature: float
    apparent_temperature: float
    precipitation: float              # mm/h
    weather_code: int
    surface_condition: SurfaceCondition
    is_green_window: bool             # Whether this hour is optimal for workout


class CardioAnalysisReport(BaseModel):
    """Complete analytical cardio report for a city."""
    city_key: str
    city_name: str
    region: Optional[str] = None
    overall_score: int                # 0..100 composite RunScore
    score_label: str                  # "Идеально", "Хорошо", "Умеренно", "Экстрим"
    score_color: str
    verdict_summary: str
    
    # Air vs Weather Breakdown
    air_quality_score: int            # 0..100
    air_quality_summary: str          # Explanation of main pollutant & lung impact
    dominant_pollutant: Optional[str] = None
    nmu_active: bool = False
    
    weather_score: int                # 0..100
    weather_summary: str              # Thermal and precipitation context
    temperature: float
    apparent_temperature: float
    thermal_zone: ThermalZone
    surface_condition: SurfaceCondition
    surface_label: str
    requires_surface_check: bool = False
    precipitation_mm: float
    wind_speed_kmh: float
    wind_gusts_kmh: float
    
    # Best & Worst Windows
    best_window_today: Optional[str] = None
    worst_window_today: Optional[str] = None
    
    # Profiles & Action Items
    recommendations: Dict[str, CardioRecommendation] = Field(default_factory=dict)
    hourly_timeline: List[CardioHourScore] = Field(default_factory=list)
    hydration_ml_per_hour: int = 500
    gear_checklist: List[str] = Field(default_factory=list)
    safety_rules: List[str] = Field(default_factory=list)
