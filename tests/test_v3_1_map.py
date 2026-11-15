"""Tests for AirTrace v3.1 Interactive Map feature."""

import json
import pytest
from fastapi.testclient import TestClient

from web.web_app import app

client = TestClient(app)


def test_index_page_contains_interactive_map_elements():
    """Verify that the index page renders the interactive map container and controls."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # View switcher buttons
    assert 'id="catalog-view-grid-btn"' in html
    assert 'id="catalog-view-map-btn"' in html
    assert "Интерактивная карта" in html
    assert "v3.1" in html

    # Map wrapper & canvas
    assert 'id="catalog-map-wrapper"' in html
    assert 'id="airtrace-russia-map"' in html

    # Filter chips
    assert 'data-filter="all"' in html
    assert 'data-filter="major"' in html
    assert 'data-filter="favorites"' in html
    assert 'data-filter="attention"' in html

    # Reset bounds button & legend
    assert 'id="map-reset-bounds-btn"' in html
    assert "Легенда" in html or "Качество воздуха:" in html

    # Leaflet assets
    assert "leaflet" in html
    assert 'id="cities-map-data"' in html


def test_cities_map_data_json_integrity():
    """Verify that the embedded cities map data is valid JSON with required fields."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # Extract JSON between script tags
    start_tag = '<script id="cities-map-data" type="application/json">'
    end_tag = "</script>"
    assert start_tag in html

    start_idx = html.index(start_tag) + len(start_tag)
    end_idx = html.index(end_tag, start_idx)
    raw_json = html[start_idx:end_idx].strip()

    cities = json.loads(raw_json)
    assert isinstance(cities, list)
    assert len(cities) >= 70

    # Verify key cities and field types
    city_keys = {c["key"]: c for c in cities}
    for required_key in ["moscow", "spb", "kazan", "novosibirsk"]:
        assert required_key in city_keys
        city = city_keys[required_key]
        assert "name" in city and isinstance(city["name"], str)
        assert "lat" in city and isinstance(city["lat"], (int, float))
        assert "lon" in city and isinstance(city["lon"], (int, float))
        assert -90 <= city["lat"] <= 90
        assert -180 <= city["lon"] <= 180
        assert "is_major" in city and isinstance(city["is_major"], bool)
