"""Integration and contract tests for AirTrace v3 API."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from schemas import (
    AQIInfo,
    AirQualityData,
    LocationInfo,
    PollutantData,
    ResponseMetadata,
    WeatherInfo,
)

client = TestClient(app)


def _mock_air_quality(lat: float = 55.7558, lon: float = 37.6176, aqi_val: int = 42) -> AirQualityData:
    return AirQualityData(
        timestamp=datetime.now(timezone.utc),
        location=LocationInfo(latitude=lat, longitude=lon),
        aqi=AQIInfo(value=aqi_val, category="Хорошо", color="#00E400", description="Качество воздуха хорошее"),
        pollutants=PollutantData(pm2_5=9.5, pm10=18.0, no2=14.0, so2=4.0, o3=40.0),
        weather=WeatherInfo(location_name="Mock City"),
        recommendations="Отличное время для прогулок",
        nmu_risk="none",
        health_warnings=[],
        metadata=ResponseMetadata(data_source="mock", freshness="fresh", confidence=0.95),
    )


def test_v3_cities_list_all():
    response = client.get("/v3/cities")
    assert response.status_code == 200
    assert response.headers["X-AirTrace-API-Version"] == "3"
    assert response.headers["X-AirTrace-Contract"] == "v3-public"

    data = response.json()
    assert data["total"] >= 50
    assert len(data["cities"]) > 0

    city_keys = [c["key"] for c in data["cities"]]
    assert "moscow" in city_keys
    assert "spb" in city_keys
    assert "kazan" in city_keys
    assert "krasnoyarsk" in city_keys


def test_v3_cities_fuzzy_search():
    # Russian query
    resp_ru = client.get("/v3/cities?q=казань")
    assert resp_ru.status_code == 200
    data_ru = resp_ru.json()
    assert len(data_ru["cities"]) >= 1
    assert data_ru["cities"][0]["name"] == "Казань"
    assert data_ru["cities"][0]["key"] == "kazan"

    # Translit query
    resp_en = client.get("/v3/cities?q=krasnoyarsk")
    assert resp_en.status_code == 200
    data_en = resp_en.json()
    assert len(data_en["cities"]) >= 1
    assert data_en["cities"][0]["key"] == "krasnoyarsk"

    # Region search
    resp_reg = client.get("/v3/cities?q=татарстан")
    assert resp_reg.status_code == 200
    data_reg = resp_reg.json()
    reg_keys = [c["key"] for c in data_reg["cities"]]
    assert "kazan" in reg_keys


def test_v3_activity_advisories_by_city():
    mock_data = _mock_air_quality(aqi_val=45)
    with patch("api.v3.routes.query_current_air_quality", AsyncMock(return_value=mock_data)):
        response = client.get("/v3/activities/advice?city=moscow")
        assert response.status_code == 200
        assert response.headers["X-AirTrace-API-Version"] == "3"

        data = response.json()
        assert data["aqi"] == 45
        assert "summary" in data
        assert "activities" in data
        assert len(data["activities"]) == 5

        categories = [act["category"] for act in data["activities"]]
        assert "outdoor_sports" in categories
        assert "ventilation" in categories
        assert "masks" in categories
        assert "air_purifier" in categories
        assert "sensitive_groups" in categories


def test_v3_current_air_quality_by_city_name():
    mock_data = _mock_air_quality(lat=55.7887, lon=49.1221, aqi_val=35)
    with patch("api.v3.routes.query_current_air_quality", AsyncMock(return_value=mock_data)):
        response = client.get("/v3/current?city=kazan")
        assert response.status_code == 200
        assert response.headers["X-AirTrace-API-Version"] == "3"

        data = response.json()
        assert data["city_name"] == "Казань"
        assert data["api_version"] == "3.0"
        assert "advisory" in data
        assert data["advisory"]["aqi"] == 35
        assert "pollutants" in data


def test_v3_current_air_quality_by_coordinates():
    mock_data = _mock_air_quality(lat=55.7558, lon=37.6176, aqi_val=50)
    with patch("api.v3.routes.query_current_air_quality", AsyncMock(return_value=mock_data)):
        response = client.get("/v3/current?lat=55.7558&lon=37.6176")
        assert response.status_code == 200
        data = response.json()
        assert data["location"]["latitude"] == pytest.approx(55.7558, abs=0.01)
        assert data["location"]["longitude"] == pytest.approx(37.6176, abs=0.01)
        assert "advisory" in data


def test_v3_forecast_with_summary():
    mock_items = [_mock_air_quality(aqi_val=30 + i) for i in range(24)]
    with patch("api.v3.routes.query_forecast_air_quality", AsyncMock(return_value=mock_items)):
        response = client.get("/v3/forecast?city=moscow&hours=24")
        assert response.status_code == 200
        assert response.headers["X-AirTrace-API-Version"] == "3"

        data = response.json()
        assert "summary" in data
        assert data["summary"]["peak_aqi"] == 53
        assert "safest_hour" in data["summary"]
        assert len(data["items"]) == 24


def test_v3_national_ranking():
    from application.queries.ranking import record_city_ranking_snapshot
    record_city_ranking_snapshot(key="moscow", name="Москва", lat=55.75, lon=37.61, aqi=42, aqi_category="Хорошо", aqi_color="#00E400")
    record_city_ranking_snapshot(key="spb", name="Санкт-Петербург", lat=59.93, lon=30.33, aqi=28, aqi_category="Хорошо", aqi_color="#00E400")

    response = client.get("/v3/cities/ranking")
    assert response.status_code == 200
    assert response.headers["X-AirTrace-API-Version"] == "3"

    data = response.json()
    assert data["cities_count"] > 0
    assert "average_aqi" in data
    assert "cleanest_cities" in data
    assert len(data["cleanest_cities"]) > 0
    assert "attention_cities" in data


def test_v3_health():
    response = client.get("/v3/health")
    assert response.status_code == 200
    assert response.headers["X-AirTrace-API-Version"] == "3"
    data = response.json()
    assert "status" in data


def test_v3_city_not_found():
    response = client.get("/v3/current?city=nonexistent_city_xyz")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data or "message" in data
