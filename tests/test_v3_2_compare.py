"""Tests for AirTrace v3.2 Multi-City Comparison feature."""

import json
import pytest
from fastapi.testclient import TestClient

from web.web_app import app

client = TestClient(app)


def test_compare_page_two_cities_v3_2_elements():
    """Verify that /compare renders the v3.2 verdict, multi-series chart and lifestyle matrix."""
    response = client.get("/compare?cities=moscow,spb")
    assert response.status_code == 200
    html = response.text

    # Preserved contract
    assert html.count("AQI сейчас") == 2

    # v3.2 Feature elements
    assert "Аналитический вердикт" in html
    assert "Лидер чистоты:" in html
    assert 'id="compare-multiline-chart"' in html
    assert "Сравнительный почасовой прогноз на 24 часа" in html
    assert "Сравнение рекомендаций для повседневной жизни" in html
    assert "Спорт на улице" in html
    assert "Проветривание" in html
    assert "Маски и защита" in html
    assert "Очиститель воздуха" in html

    # City search and remove buttons
    assert 'id="compare-search-input"' in html
    assert 'id="compare-autocomplete-box"' in html
    assert 'id="compare-forecast-data"' in html
    assert 'id="compare-all-cities-data"' in html


def test_compare_page_four_cities_rendering():
    """Verify that /compare supports up to 4 cities concurrently."""
    response = client.get("/compare?cities=moscow,spb,kazan,krasnoyarsk")
    assert response.status_code == 200
    html = response.text

    assert html.count("AQI сейчас") == 4
    assert "Москва" in html
    assert "Санкт-Петербург" in html
    assert "Казань" in html
    assert "Красноярск" in html


def test_compare_forecast_data_json_integrity():
    """Verify that the embedded multi-city forecast data is valid JSON with series info."""
    response = client.get("/compare?cities=moscow,spb")
    assert response.status_code == 200
    html = response.text

    start_tag = '<script id="compare-forecast-data" type="application/json">'
    end_tag = "</script>"
    assert start_tag in html

    start_idx = html.index(start_tag) + len(start_tag)
    end_idx = html.index(end_tag, start_idx)
    raw_json = html[start_idx:end_idx].strip()

    series = json.loads(raw_json)
    assert isinstance(series, list)
    assert len(series) == 2

    for item in series:
        assert "key" in item
        assert "name" in item
        assert "color" in item
        assert "points" in item
        assert isinstance(item["points"], list)
