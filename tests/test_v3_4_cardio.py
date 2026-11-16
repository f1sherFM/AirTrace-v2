"""Tests for AirTrace v3.4 Cardio & Outdoor Running/Walking Engine."""

import pytest
from fastapi.testclient import TestClient

from domain.cardio import (
    ActivityLevel,
    SurfaceCondition,
    ThermalZone,
    calculate_run_score,
    determine_surface_condition,
    determine_thermal_zone,
    generate_activity_recommendations,
)
from main import app

client = TestClient(app)


def test_thermal_zone_siberian_calibration():
    """Verify that thermal zones reflect realistic Siberian cold tolerance thresholds."""
    assert determine_thermal_zone(-30.0) == ThermalZone.EXTREME_FREEZE
    assert determine_thermal_zone(-24.5) == ThermalZone.EXTREME_FREEZE
    assert determine_thermal_zone(-24.0) == ThermalZone.EXTREME_FREEZE

    # -15°C to -23.9°C: Tolerable solid freeze (workable with face buff)
    assert determine_thermal_zone(-23.0) == ThermalZone.DEEP_FREEZE
    assert determine_thermal_zone(-21.0) == ThermalZone.DEEP_FREEZE
    assert determine_thermal_zone(-18.0) == ThermalZone.DEEP_FREEZE
    assert determine_thermal_zone(-15.0) == ThermalZone.DEEP_FREEZE

    # -1°C to -14.9°C: Standard energetic winter running
    assert determine_thermal_zone(-14.0) == ThermalZone.MILD_WINTER
    assert determine_thermal_zone(-10.0) == ThermalZone.MILD_WINTER
    assert determine_thermal_zone(-3.0) == ThermalZone.MILD_WINTER

    # Other zones
    assert determine_thermal_zone(2.0) == ThermalZone.MILD_CHILL
    assert determine_thermal_zone(10.0) == ThermalZone.COOL_OPTIMAL
    assert determine_thermal_zone(18.0) == ThermalZone.WARM
    assert determine_thermal_zone(28.0) == ThermalZone.HEAT


def test_surface_condition_detection():
    """Verify surface conditions and safety classifications from weather codes and temp."""
    # Freezing rain / Glaze code 66 -> ICE
    surface, ptype, label = determine_surface_condition(weather_code=66, temp=-2.0, precip_mm=1.0)
    assert surface == SurfaceCondition.ICE
    assert "гололедица" in label.lower()

    # Dry weather
    surface, ptype, label = determine_surface_condition(weather_code=0, temp=12.0, precip_mm=0.0)
    assert surface == SurfaceCondition.DRY
    assert "сухой" in label.lower()

    # Heavy rain
    surface, ptype, label = determine_surface_condition(weather_code=65, temp=15.0, precip_mm=6.0)
    assert surface == SurfaceCondition.WET
    assert "ливень" in label.lower()

    # Slush around zero with snow
    surface, ptype, label = determine_surface_condition(weather_code=71, temp=0.0, precip_mm=1.0)
    assert surface == SurfaceCondition.SLUSH
    assert "слякоть" in label.lower()


def test_run_score_weights_and_safety_caps():
    """Verify that RunScore calculates correctly and respects safety caps."""
    # 1. Ideal conditions: clean air, optimal cool temperature, dry, gentle breeze
    score, air_s, weath_s, label = calculate_run_score(
        aqi=20,
        temp=10.0,
        apparent_temp=10.0,
        precip_mm=0.0,
        wind_kmh=8.0,
        weather_code=0,
    )
    assert score >= 90
    assert label == "Идеально"
    assert air_s == 100

    # 2. Ice / Freezing Rain safety cap: score must be capped at <= 25 even if air is 100% clean
    score_ice, _, _, label_ice = calculate_run_score(
        aqi=15,
        temp=-2.0,
        apparent_temp=-4.0,
        precip_mm=1.0,
        wind_kmh=10.0,
        weather_code=66,  # Freezing rain
    )
    assert score_ice <= 25
    assert label_ice == "Не рекомендуется"

    # 3. Extreme frost (<= -24°C): score must be capped at <= 35
    score_frost, _, _, label_frost = calculate_run_score(
        aqi=15,
        temp=-26.0,
        apparent_temp=-31.0,
        precip_mm=0.0,
        wind_kmh=10.0,
        weather_code=0,
    )
    assert score_frost <= 35
    assert label_frost == "Не рекомендуется"

    # 4. Severe smog / NMU: score capped at <= 35 even in perfect +12°C weather
    score_smog, air_smog, _, label_smog = calculate_run_score(
        aqi=160,
        temp=12.0,
        apparent_temp=12.0,
        precip_mm=0.0,
        wind_kmh=5.0,
        weather_code=0,
        nmu_active=True,
    )
    assert score_smog <= 35
    assert air_smog <= 30
    assert label_smog == "Не рекомендуется"


def test_activity_recommendations_differentiation():
    """Verify that Walking, Jogging, and Tempo Run receive differentiated advice."""
    # Under deep freeze (-18°C) with clean air:
    # Jogging is 'good' with buff, Tempo is 'danger' (bronchial spasm), Walking is 'optimal' or 'good'
    recs = generate_activity_recommendations(
        overall_score=70,
        air_score=90,
        thermal_zone=ThermalZone.DEEP_FREEZE,
        surface=SurfaceCondition.COMPACT_SNOW,
        temp=-18.0,
        apparent_temp=-23.0,
        aqi=30,
        nmu_active=False,
    )
    assert "walking" in recs
    assert "jogging" in recs
    assert "tempo_run" in recs

    assert recs["walking"].status == "optimal"
    assert recs["jogging"].status == "good"
    assert any("бафф" in t.lower() for t in recs["jogging"].gear_tips)

    # Tempo run must be blocked during -18°C
    assert recs["tempo_run"].status == "danger"
    assert recs["tempo_run"].max_duration_minutes == 0


def test_api_v3_cardio_endpoint():
    """Verify that /v3/cardio/{city} returns full cardio report with V3 headers."""
    response = client.get("/v3/cardio/moscow")
    assert response.status_code == 200
    assert response.headers.get("X-AirTrace-API-Version") == "3"

    data = response.json()
    assert data["city_key"] == "moscow"
    assert data["city_name"] == "Москва"
    assert "overall_score" in data
    assert 0 <= data["overall_score"] <= 100
    assert "score_label" in data
    assert "air_quality_summary" in data
    assert "weather_summary" in data
    assert "thermal_zone" in data
    assert "surface_condition" in data
    assert "recommendations" in data
    assert "walking" in data["recommendations"]
    assert "jogging" in data["recommendations"]
    assert "tempo_run" in data["recommendations"]
    assert len(data["hourly_timeline"]) > 0
    assert len(data["gear_checklist"]) > 0


def test_api_v3_cardio_city_not_found():
    """Verify that /v3/cardio returns 404 for unknown city key."""
    response = client.get("/v3/cardio/nonexistent_unknown_city")
    assert response.status_code == 404
