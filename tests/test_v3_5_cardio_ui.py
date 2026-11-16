"""Tests for AirTrace v3.5 Dedicated Outdoor Cardio & Running UI Dashboard."""

import pytest
from fastapi.testclient import TestClient

from web.web_app import app

client = TestClient(app)


def test_running_default_page_renders_successfully():
    """Verify that GET /running renders 200 OK with default city (Moscow)."""
    response = client.get("/running")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    html = response.text

    assert "AirTrace Cardio Engine v3.5" in html
    assert "RunScore" in html
    assert "Зелёные окна" in html
    assert "Ходьба и прогулка" in html
    assert "Легкий бег" in html
    assert "Темповый бег" in html
    assert "Чек-лист экипировки" in html
    assert "Правило 250 метров" in html


def test_running_city_novosibirsk_renders():
    """Verify that GET /running/novosibirsk renders correctly with Siberian calibration."""
    response = client.get("/running/novosibirsk")
    assert response.status_code == 200
    html = response.text

    assert "Новосибирск" in html
    assert "RunScore" in html
    assert "Сибирская калибровка" in html


def test_running_city_spb_renders():
    """Verify that GET /running/spb renders successfully."""
    response = client.get("/running/spb")
    assert response.status_code == 200
    html = response.text

    assert "Санкт-Петербург" in html
    assert "RunScore" in html


def test_running_invalid_city_graceful_fallback():
    """Verify that GET /running/nonexistent_xyz falls back gracefully without 500."""
    response = client.get("/running/nonexistent_xyz")
    assert response.status_code == 200
    html = response.text
    assert "RunScore" in html


def test_city_page_has_cardio_teaser():
    """Verify that GET /city/moscow includes the cardio teaser linking to /running/moscow."""
    response = client.get("/city/moscow")
    assert response.status_code == 200
    html = response.text

    assert "RunScore" in html
    assert "/running/moscow" in html
    assert "Открыть кардио-дашборд" in html


def test_navigation_bar_has_cardio_link():
    """Verify that the header in base.html includes the 'Бег и ходьба' navigation link."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert "/running" in html
    assert "Бег и ходьба" in html
