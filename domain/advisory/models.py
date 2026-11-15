"""Models for activity and lifestyle health advisories in AirTrace v3."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    OUTDOOR_SPORTS = "outdoor_sports"
    VENTILATION = "ventilation"
    MASKS = "masks"
    AIR_PURIFIER = "air_purifier"
    SENSITIVE_GROUPS = "sensitive_groups"


class ActivityStatus(str, Enum):
    OPTIMAL = "optimal"       # Безопасно, рекомендуется
    MODERATE = "moderate"     # Умеренно, с осторожностью
    CAUTION = "caution"       # Неблагоприятно, снизить нагрузку
    RESTRICTED = "restricted" # Опасно, избегать


class ActivityAdvice(BaseModel):
    """Detailed advice for a specific lifestyle activity."""
    category: ActivityType
    title: str
    status: ActivityStatus
    status_label: str
    badge_color: str
    icon: str
    headline: str
    description: str
    tips: List[str] = Field(default_factory=list)


class OverallAdvisory(BaseModel):
    """Full health & lifestyle advisory response."""
    aqi: int
    aqi_category: str
    nmu_level: str
    summary: str
    generated_at: str
    activities: List[ActivityAdvice] = Field(default_factory=list)
