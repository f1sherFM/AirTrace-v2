"""Tests for AirTrace v3.6 AI Advisor Integration & API."""

import pytest
from fastapi.testclient import TestClient

from web.web_app import app
from infrastructure.ai import AirTraceAIAdvisor

client = TestClient(app)


def test_ai_consult_post_endpoint():
    """Verify POST /v3/ai/consult returns a valid structured AI consultation."""
    response = client.post("/v3/ai/consult", json={"city_key": "novosibirsk"})
    assert response.status_code == 200
    data = response.json()

    assert data["city_key"] == "novosibirsk"
    assert "city_name" in data
    assert "verdict" in data
    assert len(data["verdict"]) > 20
    assert "model" in data
    assert "cached" in data
    assert "remaining_daily" in data


def test_ai_consult_get_endpoint():
    """Verify GET /v3/ai/consult returns a valid response."""
    response = client.get("/v3/ai/consult?city=moscow")
    assert response.status_code == 200
    data = response.json()
    assert data["city_key"] == "moscow"
    assert "verdict" in data


def test_ai_consult_caching():
    """Verify that consecutive requests for the same city & question return cached results."""
    req = {"city_key": "spb", "question": "Стоит ли сейчас бежать?"}
    r1 = client.post("/v3/ai/consult", json=req)
    assert r1.status_code == 200

    r2 = client.post("/v3/ai/consult", json=req)
    assert r2.status_code == 200
    assert r2.json()["cached"] is True


def test_deterministic_fallback():
    """Verify that deterministic fallback works even without an API key."""
    advisor = AirTraceAIAdvisor(api_key="")
    from domain.cardio import analyze_city_cardio

    report = analyze_city_cardio(
        city_key="yakutsk",
        city_name="Якутск",
        region="Якутия",
        current_aqi=20,
        pollutants={"pm2_5": 5.0},
        weather_data={"temperature": -28.0, "apparent_temperature": -33.0, "weather_code": 0, "wind_speed": 5.0},
        hourly_forecast=[],
    )
    fallback = advisor._generate_deterministic_analysis("Якутск", report)
    assert "Воздух и лёгкие" in fallback
    assert "Вердикт для активности" in fallback
    assert "Экстремальный мороз" in fallback or "Якутск" in fallback


def test_running_page_has_ai_widget():
    """Verify that the /running page renders the AI advisor widget."""
    response = client.get("/running/novosibirsk")
    assert response.status_code == 200
    html = response.text
    assert "ai-advisor-container" in html
    assert "AirTrace AI Консультант" in html
    assert "gpt-oss-120b" in html


def test_city_page_has_ai_widget():
    """Verify that the /city page renders the AI advisor widget."""
    response = client.get("/city/moscow")
    assert response.status_code == 200
    html = response.text
    assert "ai-advisor-container" in html
    assert "AirTrace AI Консультант" in html
