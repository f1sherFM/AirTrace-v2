"""AirTrace v3 Activity & Health Advisory Domain Module."""

from .models import ActivityAdvice, ActivityStatus, ActivityType, OverallAdvisory
from .calculator import generate_activity_advisories

__all__ = [
    "ActivityAdvice",
    "ActivityStatus",
    "ActivityType",
    "OverallAdvisory",
    "generate_activity_advisories",
]
