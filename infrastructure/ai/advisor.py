"""AirTrace v3.6 AI Advisor Integration powered by Groq (openai/gpt-oss-120b)."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pathlib import Path

from core.env import load_repo_env
from domain.cardio.models import CardioAnalysisReport

load_repo_env(root_dir=Path(__file__).resolve().parents[2])

logger = logging.getLogger(__name__)

# Response cache: cache_key -> (timestamp, response_dict)
_AI_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}

# Sliding window rate limiter: list of timestamps of successful remote calls
_REQUEST_TIMESTAMPS: List[float] = []


class AirTraceAIAdvisor:
    """Intelligent cardio & air quality micro-advisor with caching and rate limiting."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        daily_limit: Optional[int] = None,
        cache_ttl: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.base_url = (base_url or os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1")).rstrip("/")
        self.model = model or os.getenv("AI_MODEL", "openai/gpt-oss-120b")
        self.daily_limit = daily_limit or int(os.getenv("AI_DAILY_RATE_LIMIT", "60"))
        # Cache TTL default is 300 seconds (5 minutes) for non-forced requests.
        # User interactive clicks explicitly send force_refresh=True for fresh generations.
        self.cache_ttl = cache_ttl if cache_ttl is not None else int(os.getenv("AI_CACHE_TTL_SECONDS", "300"))
        # Generous max_tokens for complete Cyrillic sentences without truncation
        self.max_tokens = max_tokens or int(os.getenv("AI_MAX_TOKENS", "1200"))

    def _clean_rate_limiter(self, now: float) -> int:
        """Purge timestamps older than 24h and return remaining quota."""
        global _REQUEST_TIMESTAMPS
        cutoff = now - 86400.0
        _REQUEST_TIMESTAMPS = [ts for ts in _REQUEST_TIMESTAMPS if ts > cutoff]
        return max(0, self.daily_limit - len(_REQUEST_TIMESTAMPS))

    def _make_cache_key(self, city_key: str, question: Optional[str]) -> str:
        q_norm = (question or "default_review").strip().lower()
        q_hash = hashlib.md5(q_norm.encode("utf-8")).hexdigest()[:8]
        return f"{city_key}:{q_hash}"

    async def consult(
        self,
        *,
        city_name: str,
        city_key: str,
        report: CardioAnalysisReport,
        user_question: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Generate structured expert takeaway for outdoor cardio & lung health."""
        now = time.time()
        cache_key = self._make_cache_key(city_key, user_question)

        # 1. Check in-memory cache (bypassed if force_refresh is True or cache_ttl <= 0)
        if not force_refresh and self.cache_ttl > 0 and cache_key in _AI_CACHE:
            cached_at, cached_data = _AI_CACHE[cache_key]
            if now - cached_at < self.cache_ttl:
                remaining = self._clean_rate_limiter(now)
                return {
                    **cached_data,
                    "cached": True,
                    "remaining_daily": remaining,
                }

        # 2. Check rate limit
        remaining = self._clean_rate_limiter(now)
        if remaining <= 0:
            logger.warning("AirTrace AI daily rate limit reached (%d calls). Falling back to deterministic engine.", self.daily_limit)
            fallback = self._generate_deterministic_analysis(city_name, report, user_question)
            return {
                "verdict": fallback,
                "model": "airtrace-expert-rules (limit reached)",
                "cached": False,
                "remaining_daily": 0,
                "generated_at": datetime.now(timezone.utc).strftime("%H:%M МСК"),
            }

        # 3. If no API key is provided, use deterministic engine
        if not self.api_key or self.api_key.startswith("your_"):
            logger.info("GROQ_API_KEY is not configured. Using deterministic expert rules.")
            fallback = self._generate_deterministic_analysis(city_name, report, user_question)
            return {
                "verdict": fallback,
                "model": "airtrace-expert-rules",
                "cached": False,
                "remaining_daily": remaining,
                "generated_at": datetime.now(timezone.utc).strftime("%H:%M МСК"),
            }

        # 4. Call Groq API with openai/gpt-oss-120b
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(city_name, report, user_question)

        try:
            async with httpx.AsyncClient(trust_env=True, timeout=httpx.Timeout(15.0, connect=6.0)) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.75,
                    "max_tokens": self.max_tokens,
                }
                resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

                message = data["choices"][0]["message"]
                ai_text = message.get("content", "").strip()
                if not ai_text:
                    ai_text = self._generate_deterministic_analysis(city_name, report, user_question)

                _REQUEST_TIMESTAMPS.append(now)
                new_remaining = max(0, self.daily_limit - len(_REQUEST_TIMESTAMPS))

                result = {
                    "verdict": ai_text,
                    "model": self.model,
                    "cached": False,
                    "remaining_daily": new_remaining,
                    "generated_at": datetime.now(timezone.utc).strftime("%H:%M МСК"),
                }

                _AI_CACHE[cache_key] = (now, result)
                return result

        except Exception as exc:
            logger.warning("Groq API request failed: %s. Falling back to deterministic engine.", exc)
            fallback = self._generate_deterministic_analysis(city_name, report, user_question)
            return {
                "verdict": fallback,
                "model": "airtrace-expert-rules (fallback)",
                "cached": False,
                "remaining_daily": remaining,
                "generated_at": datetime.now(timezone.utc).strftime("%H:%M МСК"),
            }

    def _build_system_prompt(self) -> str:
        return (
            "Ты — AirTrace AI, персональный спортивный консультант и врач-пульмонолог для бегунов и любителей активного отдыха в городах России и Сибири.\n\n"
            "ГЛАВНАЯ ЦЕЛЬ:\n"
            "Давать живые, глубокие, практические экспертные советы, помогая человеку сохранить здоровье лёгких, дыхательных путей и суставов при физической активности и проветривании.\n\n"
            "КРИТИЧЕСКИ ВАЖНО (НЕ ПОВТОРЯЙ ДАННЫЕ С САЙТА):\n"
            "1. Пользователь УЖЕ видит на экране все числовые плашки (RunScore, температуру, скорость ветра, чистоту воздуха). НЕ пересказывай сухие цифры в лоб и не копируй шаблонные фразы сайта! Объясняй физиологический смысл условий и конкретные действия.\n"
            "2. Пиши естественным языком живого эксперта. НЕ используй принудительные заголовки вроде '1. Воздух и лёгкие', '2. Вердикт для тренировки', '3. Зелёное окно'. Подавай ответ мягко — 2-3 связных, насыщенных пользой абзаца, выделяя ключевые мысли жирным шрифтом и аккуратными маркерами списка при перечислении экипировки или правил.\n"
            "3. Отвечай точно на вопрос пользователя. Если спросили про экипировку — разбери слои и защиту открытых зон; если про бег — тактику темпа и дыхания; если про проветривание — технику залпового воздухообмена.\n\n"
            "МЕДИЦИНСКАЯ И СИБИРСКАЯ СПЕЦИФИКА:\n"
            "- Чистота воздуха: при беге объём вентиляции лёгких вырастает до 60–100 л/мин. При смоге, взвесях PM2.5/PM10 или температурной инверсии (НМУ) форсированное дыхание приводит к глубокой ингаляции ультрадисперсных токсинов в альвеолы. При загрязнении рекомендуй парки вдали от трасс (правило 250м) или перенос в манеж.\n"
            "- Сибирский климат и дыхание: от -15°C до -23°C — привычный рабочий сибирский мороз. Бегать можно при условии носового дыхания или дыхания через бафф/балаклаву для согревания входящего воздуха. Ниже -24°C — экстрим: высокий риск рефлекторного холодового бронхоспазма, интенсивный бег противопоказан.\n"
            "- Реальность покрытия дорог: в холодный сезон (при температуре около 0°C и ниже) чистого сухого асфальта в городах практически не бывает. Ночью мог быть снег, на тротуарах снежный накат, замерзшие лужи или реагентная слякоть. Напоминай проверять сцепление обуви, использовать кроссовки с глубоким протектором (трейловые) и аккуратно проходить повороты во избежание травм связок.\n"
            "- Экипировка: принцип трёх слоёв (влагоотводящая синтетика к телу, утепляющий флис, ветрозащитная мембрана). Никакого хлопка! Обязательно закрывать ахилловы сухожилия и колени.\n"
            "- Проветривание: рекомендуй короткое залповое сквозное проветривание (5–10 минут при настежь открытых окнах) в часы спада автомобильного трафика, а не щелевое часами, чтобы сменить воздух без выстуживания стен.\n"
            "- Полнота ответа: всегда доводи все мысли, рекомендации и пункты списков до логического завершения, аккуратно закрывай структуру и никогда не обрывай предложения на полуслове."
        )

    def _build_user_prompt(
        self,
        city_name: str,
        report: CardioAnalysisReport,
        user_question: Optional[str],
    ) -> str:
        question_text = f"Вопрос пользователя: \"{user_question}\"" if user_question else "Сделай краткий экспертный разбор текущих условий и дай главные практические рекомендации."
        salt = int(time.time() * 10) % 1000

        return (
            f"Город: {city_name} ({report.region or 'Россия'}). [запрос #{salt}]\n"
            f"Текущие условия: Температура {report.temperature:.1f}°C (ощущается как {report.apparent_temperature:.1f}°C), "
            f"ветер {report.wind_speed_kmh:.1f} км/ч (порывы {report.wind_gusts_kmh:.1f} км/ч), "
            f"осадки: {report.precipitation_mm:.1f} мм/ч, дорожное покрытие/сезон: {report.surface_label}.\n"
            f"Экология: RunScore {report.overall_score}/100, Индекс лёгких {report.air_quality_score}/100, "
            f"загрязнитель: {report.dominant_pollutant or 'в норме'}, НМУ: {'Да' if report.nmu_active else 'Нет'}, "
            f"зелёное окно: {report.best_window_today or 'не определено'}.\n\n"
            f"{question_text}\n"
            f"Дай глубокий, живой ответ спортивного врача без шаблонного пересказа цифр с экрана."
        )

    def _generate_deterministic_analysis(
        self,
        city_name: str,
        report: CardioAnalysisReport,
        user_question: Optional[str] = None,
    ) -> str:
        """Deterministic fallback generating high-quality structured takeaways without API."""
        score = report.overall_score
        temp = report.temperature
        surface = report.surface_condition.value

        # 1. Air section
        if report.air_quality_score >= 80:
            air_part = f"🫁 **Воздух и лёгкие**: В г. {city_name} сейчас отличный чистый воздух ({report.air_quality_score}/100). Микрочастицы PM2.5 в пределах нормы, дыхательные пути защищены, вентиляция лёгких безопасна."
        elif report.air_quality_score >= 55:
            air_part = f"🫁 **Воздух и лёгкие**: Качество воздуха в г. {city_name} умеренное ({report.air_quality_score}/100). Присутствует фоновая запылённость, для интенсивных тренировок выбирайте лесопарковые зоны вдали от трасс."
        else:
            air_part = f"🫁 **Воздух и лёгкие**: Внимание! Зафиксировано загрязнение воздуха ({report.air_quality_score}/100, приоритет {report.dominant_pollutant or 'PM2.5'}). Глубокое форсированное дыхание на улице не рекомендуется."

        # 2. Activity / Weather part
        if surface == "ice":
            run_part = "🏃 **Вердикт для активности**: Бег на улице **не рекомендуется из-за гололедицы**. Риск падений и растяжения связок перевешивает любую пользу. Рекомендуется перейти на беговую дорожку или аккуратную ходьбу в обуви с шипами."
        elif temp <= -24.0:
            run_part = f"🏃 **Вердикт для активности**: Экстремальный мороз ({temp:.1f}°C). Высокая опасность рефлекторного спазма бронхов при ротовом дыхании. Темповые и интервальные пробежки отменяются, прогулка допустима только в плотном баффе."
        elif -23.9 <= temp <= -15.0:
            run_part = f"🏃 **Вердикт для активности**: Сибирский рабочий мороз ({temp:.1f}°C). Бег возможен для подготовленных людей. **Обязателен бафф на нос и горло** для согревания вдыхаемого воздуха, плотные варежки, тренировка до 45 минут без пауз."
        elif score >= 75:
            run_part = f"🏃 **Вердикт для активности**: Отличные условия для кардио! RunScore {score}/100. Разрешены все типы тренировок: ходьба, восстановительный кросс и интервалы. Одевайтесь по слоям под {temp:.1f}°C."
        else:
            run_part = f"🏃 **Вердикт для активности**: RunScore {score}/100 ({report.score_label}). Рекомендуется ограничиться легкой трусцой или бодрой прогулкой, контролируя пульс и дыхание."

        # 3. Timing part
        best = report.best_window_today or "утренние часы"
        time_part = f"⏰ **Зелёное окно**: Оптимальный интервал для тренировки или проветривания — **{best}**."

        return f"{air_part}\n\n{run_part}\n\n{time_part}"


# Global singleton instance
ai_advisor = AirTraceAIAdvisor()
