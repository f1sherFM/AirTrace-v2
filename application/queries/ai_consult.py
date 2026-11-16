"""Query service for AirTrace v3.6 AI cardio & air quality consultation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from application.queries.cardio import get_city_cardio_analysis
from core.settings import get_cities_mapping
from infrastructure.ai import ai_advisor

logger = logging.getLogger(__name__)


async def get_ai_consultation(
    city_key: str,
    question: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve cardio telemetry for a city and generate AI consultation."""
    cities_map = get_cities_mapping()
    norm_key = (city_key or "moscow").strip().lower()
    if norm_key not in cities_map:
        norm_key = "moscow"

    city_name = cities_map[norm_key].get("name", norm_key)
    report = await get_city_cardio_analysis(norm_key)

    result = await ai_advisor.consult(
        city_name=city_name,
        city_key=norm_key,
        report=report,
        user_question=question,
    )

    return {
        "city_key": norm_key,
        "city_name": city_name,
        **result,
    }
