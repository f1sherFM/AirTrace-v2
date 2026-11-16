"""Domain calculations for cardio, running, and outdoor activity suitability in AirTrace v3.4."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    ActivityLevel,
    CardioAnalysisReport,
    CardioHourScore,
    CardioRecommendation,
    PrecipitationType,
    SurfaceCondition,
    ThermalZone,
)


def determine_thermal_zone(temp: float) -> ThermalZone:
    """Classify ambient temperature into a thermal zone with Siberian calibration."""
    if temp <= -24.0:
        return ThermalZone.EXTREME_FREEZE
    if temp <= -15.0:
        return ThermalZone.DEEP_FREEZE
    if temp <= -1.0:
        return ThermalZone.MILD_WINTER
    if temp <= 4.9:
        return ThermalZone.MILD_CHILL
    if temp <= 14.9:
        return ThermalZone.COOL_OPTIMAL
    if temp <= 23.9:
        return ThermalZone.WARM
    return ThermalZone.HEAT


def determine_surface_condition(
    weather_code: int,
    temp: float,
    precip_mm: float,
) -> Tuple[SurfaceCondition, PrecipitationType, str]:
    """
    Determine running surface condition and precipitation type from WMO code and telemetry.
    Returns: (SurfaceCondition, PrecipitationType, human_label)
    """
    # Freezing rain / Glaze (WMO codes 56, 57, 66, 67)
    if weather_code in (56, 57, 66, 67):
        return SurfaceCondition.ICE, PrecipitationType.FREEZING_RAIN, "Гололедица / ледяной дождь"

    # Snow codes (71, 73, 75, 77, 85, 86)
    if weather_code in (71, 73, 75, 77, 85, 86) or (precip_mm > 0 and temp <= -1.0):
        if weather_code in (75, 86) or precip_mm >= 3.0:
            return SurfaceCondition.COMPACT_SNOW, PrecipitationType.BLIZZARD, "Снегопад / метель"
        if -2.0 <= temp <= 1.5:
            return SurfaceCondition.SLUSH, PrecipitationType.SNOW, "Снежная слякоть / каша"
        return SurfaceCondition.COMPACT_SNOW, PrecipitationType.SNOW, "Укатанный сухой снег"

    # Rain codes (61, 63, 65, 80, 81, 82, 95, 96, 99)
    if weather_code in (65, 82, 95, 96, 99) or precip_mm >= 5.0:
        return SurfaceCondition.WET, PrecipitationType.HEAVY_RAIN, "Сильный ливень / глубокие лужи"
    if weather_code in (61, 63, 80, 81) or precip_mm >= 1.5:
        return SurfaceCondition.WET, PrecipitationType.RAIN, "Умеренный дождь / мокрый асфальт"
    if weather_code in (51, 53, 55) or (0.1 <= precip_mm < 1.5):
        return SurfaceCondition.DAMP, PrecipitationType.DRIZZLE, "Мелкая морось / влажный асфальт"

    # Sub-zero thaw / freeze transition without active precip
    if -1.5 <= temp <= 0.5:
        return SurfaceCondition.DAMP, PrecipitationType.NONE, "Переход через ноль (возможна наледь)"

    return SurfaceCondition.DRY, PrecipitationType.NONE, "Сухой асфальт / чистое покрытие"


def calculate_run_score(
    *,
    aqi: int,
    temp: float,
    apparent_temp: float,
    precip_mm: float,
    wind_kmh: float,
    weather_code: int,
    nmu_active: bool = False,
    pm25: Optional[float] = None,
) -> Tuple[int, int, int, str]:
    """
    Calculate composite RunScore (0..100) and sub-scores.
    Formula: 40% Air + 30% Thermal + 20% Surface + 10% Wind
    Returns: (overall_score, air_score, weather_score, score_label)
    """
    # 1. Air Quality Score (0..100)
    if aqi <= 25:
        air_score = 100
    elif aqi <= 50:
        air_score = 90
    elif aqi <= 75:
        air_score = 75
    elif aqi <= 100:
        air_score = 55
    elif aqi <= 150:
        air_score = 30
    else:
        air_score = 10

    if pm25 is not None and pm25 > 35.0:
        air_score = min(air_score, 40)
    if nmu_active:
        air_score = min(air_score, 30)

    # 2. Thermal Comfort Score (0..100) with Siberian calibration
    thermal_zone = determine_thermal_zone(temp)
    if thermal_zone == ThermalZone.COOL_OPTIMAL:
        thermal_score = 100
    elif thermal_zone == ThermalZone.WARM:
        thermal_score = 92
    elif thermal_zone == ThermalZone.MILD_CHILL:
        thermal_score = 88
    elif thermal_zone == ThermalZone.MILD_WINTER:
        # -1°C .. -14°C: Standard energetic Russian winter running
        thermal_score = 82
    elif thermal_zone == ThermalZone.DEEP_FREEZE:
        # -15°C .. -23°C: Tolerable solid Siberian freeze; runnable with buff
        thermal_score = 65
    elif thermal_zone == ThermalZone.HEAT:
        # > 24°C: Thermal stress
        penalty = min(60, int((temp - 24.0) * 5))
        thermal_score = max(20, 65 - penalty)
    else:
        # EXTREME_FREEZE (<= -24°C): Dangerous for unconditioned bronchial tract
        penalty = min(70, int((abs(temp) - 24.0) * 6))
        thermal_score = max(10, 35 - penalty)

    # 3. Precipitation / Surface Score (0..100)
    surface, _, _ = determine_surface_condition(weather_code, temp, precip_mm)
    if surface == SurfaceCondition.DRY:
        precip_score = 100
    elif surface == SurfaceCondition.COMPACT_SNOW:
        precip_score = 80
    elif surface == SurfaceCondition.DAMP:
        precip_score = 80
    elif surface == SurfaceCondition.SLUSH:
        precip_score = 45
    elif surface == SurfaceCondition.WET:
        precip_score = 35
    else:  # ICE
        # Critical safety stop-factor!
        precip_score = 0

    # 4. Wind Score (0..100)
    if wind_kmh <= 15.0:
        wind_score = 100
    elif wind_kmh <= 25.0:
        wind_score = 80
    elif wind_kmh <= 35.0:
        wind_score = 55
    else:
        wind_score = 25

    # Inversion stagnation penalty: near zero wind + elevated AQI
    if wind_kmh < 4.0 and aqi >= 80:
        wind_score = max(10, wind_score - 25)

    # Composite RunScore calculation
    # Notice: if surface is ICE, total score is severely capped because slipping is dangerous
    weather_score = round(0.55 * thermal_score + 0.35 * precip_score + 0.10 * wind_score)
    raw_total = (0.40 * air_score) + (0.30 * thermal_score) + (0.20 * precip_score) + (0.10 * wind_score)
    overall_score = round(raw_total)

    if surface == SurfaceCondition.ICE:
        overall_score = min(overall_score, 25)
    if thermal_zone == ThermalZone.EXTREME_FREEZE:
        overall_score = min(overall_score, 35)
    if nmu_active:
        overall_score = min(overall_score, 35)

    overall_score = max(0, min(100, overall_score))

    if overall_score >= 80:
        score_label = "Идеально"
    elif overall_score >= 60:
        score_label = "Хорошо"
    elif overall_score >= 40:
        score_label = "Умеренно"
    else:
        score_label = "Не рекомендуется"

    return overall_score, air_score, weather_score, score_label


def generate_activity_recommendations(
    *,
    overall_score: int,
    air_score: int,
    thermal_zone: ThermalZone,
    surface: SurfaceCondition,
    temp: float,
    apparent_temp: float,
    aqi: int,
    nmu_active: bool,
) -> Dict[str, CardioRecommendation]:
    """Generate specific advice for Walking, Jogging, and Tempo Run."""
    recommendations: Dict[str, CardioRecommendation] = {}

    # 1. WALKING (Спокойная ходьба / пешие прогулки)
    walk_status = "optimal"
    walk_label = "Отлично"
    walk_color = "#10b981"
    walk_gear: List[str] = []
    walk_breathing: List[str] = ["Дыхание через нос комфортно и безопасно"]
    walk_pulse_drift = 0

    if surface == SurfaceCondition.ICE:
        walk_status = "caution"
        walk_label = "Осторожно (гололёд)"
        walk_color = "#f59e0b"
        walk_headline = "Внимание на покрытие: скользко"
        walk_desc = "Гололедица или ледяная корка. Ходите не торопясь, выбирайте посыпанные тротуары."
        walk_gear.append("Обувь с нескользящим резиновым протектором или ледоступами")
    elif thermal_zone == ThermalZone.EXTREME_FREEZE:
        walk_status = "caution"
        walk_label = "С осторожностью"
        walk_color = "#f97316"
        walk_headline = "Экстремальный мороз: утепляйтесь"
        walk_desc = f"На улице {temp:.0f}°C. Ходьба полезна, но лицо и пальцы требуют плотной защиты."
        walk_gear.extend(["Тёплые варежки", "Шерстяной шарф или бафф до самых глаз", "Термоноски"])
        walk_breathing = ["Дышите только носом, не разговаривайте на ходу"]
    elif aqi > 120 or nmu_active:
        walk_status = "caution"
        walk_label = "Смог (осторожно)"
        walk_color = "#f59e0b"
        walk_headline = "Повышенное загрязнение воздуха"
        walk_desc = "Качество воздуха снижено. Прогулка допустима в спокойном темпе, желательно в парке."
        walk_gear.append("Респиратор FFP2 при запахе гари")
    else:
        walk_headline = "Отличные условия для прогулки"
        walk_desc = "Прекрасное время для пешей прогулки на свежем воздухе для здоровья и иммунитета."
        if thermal_zone in (ThermalZone.MILD_WINTER, ThermalZone.DEEP_FREEZE):
            walk_gear.extend(["Зимняя теплая обувь", "Шапка и перчатки"])

    recommendations["walking"] = CardioRecommendation(
        activity=ActivityLevel.WALKING,
        status=walk_status,
        status_label=walk_label,
        badge_color=walk_color,
        headline=walk_headline,
        description=walk_desc,
        max_duration_minutes=90 if walk_status == "optimal" else 45,
        gear_tips=walk_gear,
        breathing_tips=walk_breathing,
        pulse_drift_bpm=walk_pulse_drift,
    )

    # 2. JOGGING (Оздоровительный бег / джоггинг)
    jog_gear: List[str] = []
    jog_breathing: List[str] = ["Равномерное носовое или смешанное дыхание"]
    jog_pulse_drift = 0

    if surface == SurfaceCondition.ICE:
        jog_status = "danger"
        jog_label = "Не рекомендуется"
        jog_color = "#ef4444"
        jog_headline = "Опасность травм из-за гололедицы"
        jog_desc = "Высокий риск падения и вывиха голеностопа. Замените уличную пробежку беговой дорожкой или манежем."
        jog_max_dur = 0
    elif thermal_zone == ThermalZone.EXTREME_FREEZE:
        jog_status = "danger"
        jog_label = "Экстремальный мороз"
        jog_color = "#ef4444"
        jog_headline = f"Мороз {temp:.0f}°C: риск для лёгких"
        jog_desc = "При глубоком дыхании на бегу морозный воздух обжигает бронхи. Перенесите тренировку в тепло."
        jog_max_dur = 25
    elif aqi > 120 or nmu_active:
        jog_status = "caution"
        jog_label = "Смог (ограничить)"
        jog_color = "#f97316"
        jog_headline = "Высокая концентрация микрочастиц"
        jog_desc = "При повышенном легочном вентилировании частицы PM2.5 проникают глубже в кровеносную систему."
        jog_max_dur = 30
        jog_pulse_drift = 6
    elif thermal_zone == ThermalZone.DEEP_FREEZE:
        jog_status = "good"
        jog_label = "Крепкий мороз"
        jog_color = "#38bdf8"
        jog_headline = f"Бодрящий мороз {temp:.0f}°C: рабочий бег"
        jog_desc = "Для привыкших к сибирской зиме людей бег комфортен. Обязательно натяните бафф на нос и рот."
        jog_max_dur = 45
        jog_gear.extend(["Бафф / термомаска на шею и лицо", "Варежки вместо перчаток", "Ветрозащитные тайтсы с начесом"])
        jog_breathing = ["Вдох через бафф для согревания входящего потока"]
    elif thermal_zone == ThermalZone.HEAT:
        jog_status = "caution"
        jog_label = "Жара"
        jog_color = "#f59e0b"
        jog_headline = f"Жарко ({temp:.0f}°C): риск перегрева"
        jog_desc = "Бегите в тенистом парке, пейте воду каждые 15 минут, контролируйте пульс."
        jog_max_dur = 40
        jog_pulse_drift = 8
        jog_gear.extend(["Кепка от солнца", "Бутылка с изотоником"])
    else:
        jog_status = "optimal"
        jog_label = "Отлично"
        jog_color = "#10b981"
        jog_headline = "Идеальное время для лёгкой пробежки"
        jog_desc = "Благоприятный баланс чистоты воздуха и температуры. Организм получит максимум пользы."
        jog_max_dur = 60
        if thermal_zone == ThermalZone.MILD_WINTER:
            jog_gear.extend(["Тонкое термобелье", "Кроссовки с цепкой подошвой", "Легкая шапка"])

    recommendations["jogging"] = CardioRecommendation(
        activity=ActivityLevel.JOGGING,
        status=jog_status,
        status_label=jog_label,
        badge_color=jog_color,
        headline=jog_headline,
        description=jog_desc,
        max_duration_minutes=jog_max_dur,
        gear_tips=jog_gear,
        breathing_tips=jog_breathing,
        pulse_drift_bpm=jog_pulse_drift,
    )

    # 3. TEMPO RUN (Интенсивный бег / темповые интервалы / VO2 Max)
    tempo_gear: List[str] = []
    tempo_breathing: List[str] = ["Предельная легочная вентиляция (до 100+ л/мин)"]
    tempo_pulse_drift = 0

    if surface in (SurfaceCondition.ICE, SurfaceCondition.SLUSH, SurfaceCondition.WET):
        tempo_status = "danger"
        tempo_label = "Не рекомендуется"
        tempo_color = "#ef4444"
        tempo_headline = "Трасса не подходит для скоростных работ"
        tempo_desc = "Скользкое или мокрое покрытие не даёт толчка стопы и провоцирует травму мышц задней поверхности бедра."
        tempo_max_dur = 0
    elif thermal_zone in (ThermalZone.EXTREME_FREEZE, ThermalZone.DEEP_FREEZE):
        tempo_status = "danger"
        tempo_label = "Слишком холодно"
        tempo_color = "#ef4444"
        tempo_headline = f"Мороз ({temp:.0f}°C) исключает интервалы"
        tempo_desc = "При темповом беге дыхание становится исключительно ротовым. Прямой вдох ледяного воздуха вызовет резкий бронхоспазм."
        tempo_max_dur = 0
    elif aqi > 75 or nmu_active:
        tempo_status = "danger"
        tempo_label = "Смог (опасно)"
        tempo_color = "#ef4444"
        tempo_headline = "Высокая токсическая нагрузка"
        tempo_desc = "При глубоком вентилировании токсины оседают в альвеолах. Высокоинтенсивный бег сегодня принесет вред, а не пользу."
        tempo_max_dur = 0
        tempo_pulse_drift = 10
    elif thermal_zone == ThermalZone.HEAT:
        tempo_status = "caution"
        tempo_label = "Жара"
        tempo_color = "#f59e0b"
        tempo_headline = "Перегрев сердечно-сосудистой системы"
        tempo_desc = "При высокой температуре сердце бьется чаще, лактат накапливается быстрее. Снизьте целевой темп на 15–20 сек/км."
        tempo_max_dur = 35
        tempo_pulse_drift = 12
    else:
        tempo_status = "optimal"
        tempo_label = "Отлично"
        tempo_color = "#10b981"
        tempo_headline = "Отличные условия для темповой тренировки"
        tempo_desc = "Воздух чистый, сцепление надежное, температура способствует быстрому отводу тепла от работающих мышц."
        tempo_max_dur = 60

    recommendations["tempo_run"] = CardioRecommendation(
        activity=ActivityLevel.TEMPO_RUN,
        status=tempo_status,
        status_label=tempo_label,
        badge_color=tempo_color,
        headline=tempo_headline,
        description=tempo_desc,
        max_duration_minutes=tempo_max_dur,
        gear_tips=tempo_gear,
        breathing_tips=tempo_breathing,
        pulse_drift_bpm=tempo_pulse_drift,
    )

    return recommendations


def analyze_city_cardio(
    *,
    city_key: str,
    city_name: str,
    region: Optional[str],
    current_aqi: int,
    pollutants: Dict[str, Any],
    weather_data: Dict[str, Any],
    hourly_forecast: List[Dict[str, Any]],
    nmu_active: bool = False,
) -> CardioAnalysisReport:
    """Complete analytical synthesis of air quality and weather telemetry into CardioReport."""
    temp = float(weather_data.get("temperature", 0.0))
    apparent_temp = float(weather_data.get("apparent_temperature", temp))
    precip_mm = float(weather_data.get("precipitation", 0.0))
    weather_code = int(weather_data.get("weather_code", 0))
    wind_kmh = float(weather_data.get("wind_speed", 10.0))
    wind_gusts = float(weather_data.get("wind_gusts", wind_kmh * 1.3))
    pm25 = pollutants.get("pm2_5")

    thermal_zone = determine_thermal_zone(temp)
    surface, precip_type, surface_label = determine_surface_condition(weather_code, temp, precip_mm)

    overall_score, air_score, weather_score, score_label = calculate_run_score(
        aqi=current_aqi,
        temp=temp,
        apparent_temp=apparent_temp,
        precip_mm=precip_mm,
        wind_kmh=wind_kmh,
        weather_code=weather_code,
        nmu_active=nmu_active,
        pm25=pm25,
    )

    score_colors = {
        "Идеально": "#10b981",
        "Хорошо": "#2dd4bf",
        "Умеренно": "#f59e0b",
        "Не рекомендуется": "#ef4444",
    }
    score_color = score_colors.get(score_label, "#38bdf8")

    # Air quality summary
    dominant = "PM2.5" if (pm25 or 0) > 20 else ("NO2" if (pollutants.get("no2") or 0) > 30 else None)
    if current_aqi <= 50:
        air_summary = f"Воздух в г. {city_name} чистый (AQI {current_aqi}). Легкие и бронхи защищены от микрочастиц."
    elif current_aqi <= 100:
        air_summary = f"Качество воздуха умеренное (AQI {current_aqi}). При глубоком дыхании на бегу есть легкая нагрузка на дыхательные пути."
    else:
        air_summary = f"Внимание: повышенная концентрация смога (AQI {current_aqi}). Интенсивное дыхание на улице нежелательно."

    # Weather summary
    if thermal_zone in (ThermalZone.MILD_WINTER, ThermalZone.DEEP_FREEZE):
        weath_summary = f"Зимняя погода: {temp:.0f}°C (ощущается как {apparent_temp:.0f}°C). Покрытие: {surface_label}."
    elif thermal_zone == ThermalZone.EXTREME_FREEZE:
        weath_summary = f"Суровый сибирский мороз: {temp:.0f}°C. Высокий риск переохлаждения открытых участков."
    elif thermal_zone == ThermalZone.HEAT:
        weath_summary = f"Жаркая погода: +{temp:.0f}°C. Повышенный пульс и быстрое обезвоживание."
    else:
        weath_summary = f"Температура: {temp:+.0f}°C (ощущается как {apparent_temp:+.0f}°C). Покрытие: {surface_label}."

    # Verdict summary
    if overall_score >= 80:
        verdict = f"Отличный момент для кардио в г. {city_name}! Чистый воздух и рабочая погода."
    elif overall_score >= 60:
        verdict = f"Условия для тренировки в г. {city_name} хорошие. Обратите внимание на экипировку по погоде."
    elif overall_score >= 40:
        verdict = f"Пограничные условия в г. {city_name}. Снизьте интенсивность или сократите время пробежки."
    else:
        verdict = f"Сегодня в г. {city_name} тренироваться на улице не рекомендуется. Лучше провести занятие в помещении."

    # Build recommendations
    recs = generate_activity_recommendations(
        overall_score=overall_score,
        air_score=air_score,
        thermal_zone=thermal_zone,
        surface=surface,
        temp=temp,
        apparent_temp=apparent_temp,
        aqi=current_aqi,
        nmu_active=nmu_active,
    )

    # Process hourly timeline (up to 24h)
    hourly_timeline: List[CardioHourScore] = []
    best_hour_score = -1
    best_hour_label = None
    worst_hour_score = 999
    worst_hour_label = None

    for item in hourly_forecast[:24]:
        ts = item.get("timestamp", "")
        hour_lbl = ts[11:16] if len(ts) >= 16 else f"{len(hourly_timeline)}:00"
        h_aqi = int(item.get("aqi", current_aqi))
        h_temp = float(item.get("temperature", temp))
        h_app_temp = float(item.get("apparent_temperature", h_temp))
        h_precip = float(item.get("precipitation", 0.0))
        h_wcode = int(item.get("weather_code", 0))
        h_wind = float(item.get("wind_speed", wind_kmh))

        h_surface, _, _ = determine_surface_condition(h_wcode, h_temp, h_precip)
        h_score, h_air, h_weath, _ = calculate_run_score(
            aqi=h_aqi,
            temp=h_temp,
            apparent_temp=h_app_temp,
            precip_mm=h_precip,
            wind_kmh=h_wind,
            weather_code=h_wcode,
            nmu_active=nmu_active,
        )

        is_green = h_score >= 70 and h_surface != SurfaceCondition.ICE
        hourly_timeline.append(
            CardioHourScore(
                timestamp=ts,
                hour_label=hour_lbl,
                run_score=h_score,
                air_score=h_air,
                weather_score=h_weath,
                aqi=h_aqi,
                temperature=h_temp,
                apparent_temperature=h_app_temp,
                precipitation=h_precip,
                weather_code=h_wcode,
                surface_condition=h_surface,
                is_green_window=is_green,
            )
        )

        if h_score > best_hour_score:
            best_hour_score = h_score
            best_hour_label = hour_lbl
        if h_score < worst_hour_score:
            worst_hour_score = h_score
            worst_hour_label = hour_lbl

    best_window = f"{best_hour_label} (RunScore {best_hour_score})" if best_hour_label else "Утро"
    worst_window = f"{worst_hour_label} (RunScore {worst_hour_score})" if worst_hour_label else "Вечерний час пик"

    # Gear checklist
    checklist = [
        "Правило 250 м: выбирайте парковые дорожки вдали от автомагистралей",
        "Дыхание: сохраняйте носовой вдох или используйте бафф при холодном воздухе",
    ]
    if surface == SurfaceCondition.ICE:
        checklist.insert(0, "⚠️ Скользко: шипы или обувь с зимним фрикционным протектором")
    elif surface in (SurfaceCondition.SLUSH, SurfaceCondition.WET):
        checklist.insert(0, "Влагозащитные кроссовки (Gore-Tex) и плотные спортивные носки")
    if thermal_zone in (ThermalZone.MILD_WINTER, ThermalZone.DEEP_FREEZE):
        checklist.append("Одежда в 2–3 слоя: термобелье (влагоотвод), флис (тепло), ветровка")
    elif thermal_zone == ThermalZone.HEAT:
        checklist.append("Кепка со светлым козырьком и солнцезащитные очки")

    hydration = 600 if thermal_zone == ThermalZone.HEAT else (450 if thermal_zone == ThermalZone.DEEP_FREEZE else 500)

    return CardioAnalysisReport(
        city_key=city_key,
        city_name=city_name,
        region=region,
        overall_score=overall_score,
        score_label=score_label,
        score_color=score_color,
        verdict_summary=verdict,
        air_quality_score=air_score,
        air_quality_summary=air_summary,
        dominant_pollutant=dominant,
        nmu_active=nmu_active,
        weather_score=weather_score,
        weather_summary=weath_summary,
        temperature=temp,
        apparent_temperature=apparent_temp,
        thermal_zone=thermal_zone,
        surface_condition=surface,
        surface_label=surface_label,
        precipitation_mm=precip_mm,
        wind_speed_kmh=wind_kmh,
        wind_gusts_kmh=wind_gusts,
        best_window_today=best_window,
        worst_window_today=worst_window,
        recommendations=recs,
        hourly_timeline=hourly_timeline,
        hydration_ml_per_hour=hydration,
        gear_checklist=checklist,
        safety_rules=[
            "Ориентируйтесь на пульс (ЧСС), а не на минутный темп: при загрязнении и морозе пульс выше",
            "Заканчивайте тренировку возле тёплого помещения, чтобы не остывать на ветру",
        ],
    )
