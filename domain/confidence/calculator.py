"""Confidence calculation domain logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ConfidenceInputs:
    data_source: str
    source_available: bool
    cache_age_seconds: int
    fallback_used: bool


class ConfidenceCalculator:
    """Pure confidence scoring logic."""

    @staticmethod
    def _source_base_score(data_source: str) -> float:
        source = (data_source or "fallback").lower()
        mapping = {
            "live": 0.95,
            "historical": 0.88,
            "forecast": 0.75,
            "fallback": 0.45,
        }
        return mapping.get(source, 0.45)

    @staticmethod
    def _calculate_age_penalty(age_seconds: int) -> float:
        age = max(0, int(age_seconds))
        if age <= 900:
            return 0.0
        elif age <= 3600:
            return 0.05 * ((age - 900) / 2700.0)
        elif age <= 10800:
            return 0.05 + 0.10 * ((age - 3600) / 7200.0)
        elif age <= 21600:
            return 0.15 + 0.15 * ((age - 10800) / 10800.0)
        else:
            return 0.30

    @staticmethod
    def _build_human_explanation(data_source: str, available: bool, age: int, fallback: bool) -> str:
        source_labels = {
            "live": "Прямой онлайн-замер",
            "historical": "Исторические данные",
            "forecast": "Модель прогноза",
            "fallback": "Резервный источник",
        }
        src_label = source_labels.get(data_source.lower(), f"Источник {data_source}")

        if age <= 900:
            age_label = "данные свежие (< 15 мин)"
        elif age <= 3600:
            age_label = f"замер {age // 60} мин назад"
        elif age <= 86400:
            age_label = f"возраст данных {age // 3600} ч"
        else:
            age_label = f"данные старше {age // 86400} дн"

        parts = [src_label, age_label]
        if not available:
            parts.append("основной источник недоступен")
        if fallback:
            parts.append("использован резерв")
        else:
            parts.append("без сбоев")

        return ", ".join(parts)

    def calculate(self, inputs: ConfidenceInputs) -> Tuple[float, str]:
        """Calculates a bounded confidence score [0.0, 1.0] and a Russian explanatory label.
        
        Note on worst-case inputs: If data_source is fallback (base 0.45) with primary
        unavailable (-0.20), maximum age penalty (-0.30), and fallback flag (-0.25),
        the raw score reaches -0.30. This is safely clamped to 0.0. The UI handles
        0.0 transparently without hiding data, presenting the exact rationale to users.
        """
        score = self._source_base_score(inputs.data_source)

        if not inputs.source_available:
            score -= 0.20

        age = max(0, int(inputs.cache_age_seconds))
        score -= self._calculate_age_penalty(age)

        if inputs.fallback_used:
            score -= 0.25

        bounded = max(0.0, min(1.0, round(score, 3)))
        explanation = self._build_human_explanation(
            data_source=inputs.data_source,
            available=inputs.source_available,
            age=age,
            fallback=inputs.fallback_used,
        )
        return bounded, explanation
