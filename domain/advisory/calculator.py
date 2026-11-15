"""Domain logic for calculating lifestyle and health advisories in AirTrace v3."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .models import ActivityAdvice, ActivityStatus, ActivityType, OverallAdvisory


def _normalize_nmu(nmu_level: Optional[str]) -> str:
    if not nmu_level:
        return "none"
    norm = nmu_level.lower().strip()
    if "критич" in norm or "critical" in norm or "blacksky" in norm:
        return "critical"
    if "высок" in norm or "high" in norm:
        return "high"
    if "средн" in norm or "medium" in norm or "moderate" in norm:
        return "medium"
    if "низк" in norm or "low" in norm:
        return "low"
    return "none"


def generate_activity_advisories(
    *,
    aqi_value: int,
    aqi_category: str = "Хорошо",
    nmu_level: Optional[str] = "none",
    pollutants: Optional[dict[str, Any]] = None,
    weather: Optional[dict[str, Any]] = None,
) -> OverallAdvisory:
    """Generate structured activity recommendations based on AQI and NMU."""
    pollutants = pollutants or {}
    weather = weather or {}
    norm_nmu = _normalize_nmu(nmu_level)
    pm25 = pollutants.get("pm2_5")

    # 1. Outdoor Sports Advice
    if aqi_value <= 50 and norm_nmu in ("none", "low"):
        sports = ActivityAdvice(
            category=ActivityType.OUTDOOR_SPORTS,
            title="Спорт на улице",
            status=ActivityStatus.OPTIMAL,
            status_label="Отлично",
            badge_color="#10B981",
            icon="activity",
            headline="Отличное время для тренировок на воздухе",
            description="Качество воздуха идеальное для пробежек, велопрогулок и любых активностей.",
            tips=["Подходит для интервального и длительного бега", "Дыхательные пути защищены чистым воздухом"],
        )
    elif aqi_value <= 100 and norm_nmu != "critical":
        sports = ActivityAdvice(
            category=ActivityType.OUTDOOR_SPORTS,
            title="Спорт на улице",
            status=ActivityStatus.MODERATE,
            status_label="Умеренно",
            badge_color="#F59E0B",
            icon="activity",
            headline="Тренировки допустимы",
            description="Качество воздуха приемлемое. Здоровым людям можно тренироваться, при одышке снизьте темп.",
            tips=["Выбирайте парки вдали от магистралей", "При признаках усталости перейдите на ходьбу"],
        )
    elif aqi_value <= 150 or norm_nmu in ("medium", "high"):
        sports = ActivityAdvice(
            category=ActivityType.OUTDOOR_SPORTS,
            title="Спорт на улице",
            status=ActivityStatus.CAUTION,
            status_label="Нежелательно",
            badge_color="#F97316",
            icon="alert-triangle",
            headline="Снизьте интенсивность или идите в зал",
            description="Воздух загрязнен. Интенсивные кардио-нагрузки на улице не рекомендуются.",
            tips=["Перенесите тренировку в зал с приточной вентиляцией", "Избегайте вечерних пробежек вдоль дорог"],
        )
    else:
        sports = ActivityAdvice(
            category=ActivityType.OUTDOOR_SPORTS,
            title="Спорт на улице",
            status=ActivityStatus.RESTRICTED,
            status_label="Опасно",
            badge_color="#EF4444",
            icon="shield-alert",
            headline="Исключите любые тренировки на улице",
            description="Опасная концентрация микрочастиц. Глубокое дыхание при беге доставляет токсины прямо в легкие.",
            tips=["Тренируйтесь только дома или в зале с HEPA-фильтрами", "Сократите любые физические усилия вне помещений"],
        )

    # 2. Window Ventilation Advice
    if aqi_value <= 50 and norm_nmu in ("none", "low"):
        vent = ActivityAdvice(
            category=ActivityType.VENTILATION,
            title="Проветривание",
            status=ActivityStatus.OPTIMAL,
            status_label="Рекомендуется",
            badge_color="#10B981",
            icon="wind",
            headline="Проветривайте свободно",
            description="Воздух за окном чистый и свежий. Рекомендуется регулярное сквозное проветривание.",
            tips=["Открывайте окна на 20-30 минут несколько раз в день", "Обновите воздух перед сном"],
        )
    elif aqi_value <= 100 and norm_nmu not in ("high", "critical"):
        vent = ActivityAdvice(
            category=ActivityType.VENTILATION,
            title="Проветривание",
            status=ActivityStatus.MODERATE,
            status_label="Ограниченно",
            badge_color="#F59E0B",
            icon="wind",
            headline="Кратковременное проветривание",
            description="Проветривайте кратковременно (10-15 минут), желательно рано утром или после осадков.",
            tips=["Избегайте часов пик (8-10 утра и 18-20 вечера)", "Используйте режим микропроветривания"],
        )
    elif aqi_value <= 150 or norm_nmu == "medium":
        vent = ActivityAdvice(
            category=ActivityType.VENTILATION,
            title="Проветривание",
            status=ActivityStatus.CAUTION,
            status_label="Нежелательно",
            badge_color="#F97316",
            icon="alert-circle",
            headline="Ограничьте открывание окон",
            description="Режим рассеивания затруднен, частицы накапливаются у земли. Открывать окна нежелательно.",
            tips=["Используйте приточные очистители воздуха (бризеры)", "Влажная уборка поможет снизить пыль в доме"],
        )
    else:
        vent = ActivityAdvice(
            category=ActivityType.VENTILATION,
            title="Проветривание",
            status=ActivityStatus.RESTRICTED,
            status_label="Закрыть окна",
            badge_color="#EF4444",
            icon="x-circle",
            headline="Держите окна плотно закрытыми",
            description="Смог и высокая концентрация ПДК. Открытые окна быстро наполнят жилье вредными взвесями.",
            tips=["Закройте окна и балконные двери", "Включите рециркуляцию в кондиционерах"],
        )

    # 3. Mask Protection Advice
    if aqi_value <= 100:
        masks = ActivityAdvice(
            category=ActivityType.MASKS,
            title="Защитная маска",
            status=ActivityStatus.OPTIMAL,
            status_label="Не требуется",
            badge_color="#10B981",
            icon="smile",
            headline="Средства защиты не требуются",
            description="Концентрация загрязнителей находится в пределах нормы для большинства людей.",
            tips=["Обычное дыхание безопасно"],
        )
    elif aqi_value <= 150:
        masks = ActivityAdvice(
            category=ActivityType.MASKS,
            title="Защитная маска",
            status=ActivityStatus.CAUTION,
            status_label="Для чувствительных",
            badge_color="#F97316",
            icon="shield",
            headline="Респиратор для чувствительных групп",
            description="Людям с астмой, аллергией и сердечными болезнями рекомендован респиратор FFP2/KN95 на улице.",
            tips=["Обычные медицинские маски не фильтруют PM2.5", "Используйте респиратор с классом защиты FFP2"],
        )
    else:
        masks = ActivityAdvice(
            category=ActivityType.MASKS,
            title="Защитная маска",
            status=ActivityStatus.RESTRICTED,
            status_label="Обязательно FFP2/3",
            badge_color="#EF4444",
            icon="shield-alert",
            headline="Надевайте респиратор FFP2 или FFP3",
            description="Высокая запыленность и токсичность воздуха. Защитите дыхательные пути плотным респиратором.",
            tips=["Убедитесь в плотном прилегании по контуру лица", "Минимизируйте время нахождения на открытом воздухе"],
        )

    # 4. Air Purifier Advice
    if aqi_value <= 50:
        purifier = ActivityAdvice(
            category=ActivityType.AIR_PURIFIER,
            title="Очиститель воздуха",
            status=ActivityStatus.OPTIMAL,
            status_label="Фоновый режим",
            badge_color="#10B981",
            icon="refresh-cw",
            headline="Фоновый режим или выключен",
            description="Качество входящего воздуха высокое, нагрузка на фильтры минимальна.",
            tips=["Достаточно стандартного авто-режима"],
        )
    elif aqi_value <= 100:
        purifier = ActivityAdvice(
            category=ActivityType.AIR_PURIFIER,
            title="Очиститель воздуха",
            status=ActivityStatus.MODERATE,
            status_label="Включить",
            badge_color="#F59E0B",
            icon="refresh-cw",
            headline="Рекомендуется включить очиститель",
            description="Включите очиститель воздуха с HEPA-фильтрацией в жилых комнатах для поддержания свежести.",
            tips=["Особенно полезно включить в спальне перед сном", "Поддерживайте влажность 40-50%"],
        )
    else:
        purifier = ActivityAdvice(
            category=ActivityType.AIR_PURIFIER,
            title="Очиститель воздуха",
            status=ActivityStatus.RESTRICTED,
            status_label="Максимум",
            badge_color="#EF4444",
            icon="zap",
            headline="Включите очиститель на повышенную мощность",
            description="Концентрация аэрозолей повышена. HEPA-фильтрация критически важна для очистки внутреннего воздуха.",
            tips=["Переведите очиститель в турбо/высокий режим", "Не открывайте форточки при работающем приборе"],
        )

    # 5. Sensitive Groups Advice
    if aqi_value <= 50:
        sensitive = ActivityAdvice(
            category=ActivityType.SENSITIVE_GROUPS,
            title="Чувствительные группы",
            status=ActivityStatus.OPTIMAL,
            status_label="Безопасно",
            badge_color="#10B981",
            icon="heart",
            headline="Безопасно для всех возрастов",
            description="Отличные условия для детей, беременных женщин, пожилых людей и людей с аллергией.",
            tips=["Полезны длительные прогулки в лесопарках"],
        )
    elif aqi_value <= 100:
        sensitive = ActivityAdvice(
            category=ActivityType.SENSITIVE_GROUPS,
            title="Чувствительные группы",
            status=ActivityStatus.MODERATE,
            status_label="Внимание",
            badge_color="#F59E0B",
            icon="heart",
            headline="Следите за самочувствием",
            description="Людям с астмой стоит контролировать дыхание и держаться подальше от оживленных дорог.",
            tips=["Держите базисную терапию при себе", "Планируйте прогулки в зеленых зонах"],
        )
    elif aqi_value <= 150:
        sensitive = ActivityAdvice(
            category=ActivityType.SENSITIVE_GROUPS,
            title="Чувствительные группы",
            status=ActivityStatus.CAUTION,
            status_label="Ограничить выход",
            badge_color="#F97316",
            icon="alert-triangle",
            headline="Сократите прогулки на улице",
            description="Повышенный риск кашля, одышки и аллергических реакций. Детям и пожилым лучше оставаться дома.",
            tips=["Исключите активные игры на уличных площадках", "При признаках ухудшения свяжитесь с врачом"],
        )
    else:
        sensitive = ActivityAdvice(
            category=ActivityType.SENSITIVE_GROUPS,
            title="Чувствительные группы",
            status=ActivityStatus.RESTRICTED,
            status_label="Оставаться дома",
            badge_color="#EF4444",
            icon="shield-alert",
            headline="Строго оставаться в закрытых помещениях",
            description="Опасная среда для людей с бронхолегочными и сердечно-сосудистыми заболеваниями.",
            tips=["Не выходите без крайней необходимости", "Контролируйте артериальное давление и сатурацию"],
        )

    # Summary
    if aqi_value <= 50 and norm_nmu in ("none", "low"):
        summary = "Отличное качество воздуха: безопасно для прогулок, проветривания и спорта."
    elif aqi_value <= 100:
        summary = "Умеренное качество воздуха: безопасно для большинства, чувствительным группам стоит снизить нагрузки."
    elif aqi_value <= 150:
        summary = "Повышенный уровень загрязнения: рекомендуется закрыть окна, воздержаться от бега на улице."
    else:
        summary = "Опасный уровень загрязнения: держите окна закрытыми, используйте HEPA-очиститель и респиратор FFP2 на улице."

    return OverallAdvisory(
        aqi=aqi_value,
        aqi_category=aqi_category,
        nmu_level=norm_nmu,
        summary=summary,
        generated_at=datetime.now(timezone.utc).isoformat(),
        activities=[sports, vent, masks, purifier, sensitive],
    )
