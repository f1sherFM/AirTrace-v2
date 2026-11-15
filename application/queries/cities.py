"""Query services for city discovery and fuzzy search in AirTrace v3."""

from __future__ import annotations

import re
from typing import Any, List, Optional
from pydantic import BaseModel

from core.settings import load_cities_config


class CitySearchItem(BaseModel):
    key: str
    name: str
    lat: float
    lon: float
    region: Optional[str] = None
    is_major: bool = False


class CitySearchResponse(BaseModel):
    total: int
    query: Optional[str] = None
    cities: List[CitySearchItem]


# Russian to Latin transliteration table for flexible search
_TRANSLIT_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _translit(text: str) -> str:
    text_lower = text.lower()
    return "".join(_TRANSLIT_MAP.get(char, char) for char in text_lower)


def search_cities(query: Optional[str] = None, limit: int = 100) -> CitySearchResponse:
    """Search cities in the centralized catalog by name, key, or region."""
    config = load_cities_config()
    all_cities = config.cities

    if not query or not query.strip():
        items = [
            CitySearchItem(
                key=city.key,
                name=city.name,
                lat=city.lat,
                lon=city.lon,
                region=city.region,
                is_major=city.is_major,
            )
            for city in all_cities.values()
        ]
        # Sort alphabetically by city name
        items.sort(key=lambda c: c.name.lower())
        return CitySearchResponse(total=len(items), query=None, cities=items[:limit])

    norm_q = query.strip().lower()
    translit_q = _translit(norm_q)

    matched: list[tuple[int, CitySearchItem]] = []

    for city in all_cities.values():
        name_lower = city.name.lower()
        key_lower = city.key.lower()
        region_lower = (city.region or "").lower()
        name_translit = _translit(name_lower)

        score = 0
        # Exact prefix match on Russian name is top score
        if name_lower.startswith(norm_q):
            score = 100
        # Exact prefix on English key
        elif key_lower.startswith(norm_q) or key_lower.startswith(translit_q):
            score = 90
        # Substring in name
        elif norm_q in name_lower:
            score = 80
        # Translit match
        elif translit_q in name_translit:
            score = 70
        # Substring in key
        elif norm_q in key_lower or translit_q in key_lower:
            score = 60
        # Substring in region
        elif region_lower and norm_q in region_lower:
            score = 50

        if score > 0:
            if city.is_major:
                score += 5  # Give slight boost to major metropolitan centers
            item = CitySearchItem(
                key=city.key,
                name=city.name,
                lat=city.lat,
                lon=city.lon,
                region=city.region,
                is_major=city.is_major,
            )
            matched.append((score, item))

    # Sort by relevance score desc, then name asc
    matched.sort(key=lambda pair: (-pair[0], pair[1].name))
    result_items = [item for _, item in matched[:limit]]

    return CitySearchResponse(total=len(result_items), query=query, cities=result_items)
