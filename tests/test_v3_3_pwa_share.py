"""Tests for AirTrace v3.3 PWA and Social Sharing features."""

import json
import pytest
from fastapi.testclient import TestClient

from web.web_app import app

client = TestClient(app)


def test_pwa_manifest_endpoint():
    """Verify that /manifest.json returns a valid PWA manifest."""
    response = client.get("/manifest.json")
    assert response.status_code == 200
    assert "application/manifest+json" in response.headers.get("content-type", "")

    manifest = response.json()
    assert manifest["short_name"] == "AirTrace"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert len(manifest["icons"]) > 0


def test_service_worker_endpoint():
    """Verify that /sw.js serves the service worker with root scope permissions."""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "application/javascript" in response.headers.get("content-type", "")
    assert response.headers.get("Service-Worker-Allowed") == "/"

    content = response.text
    assert "CACHE_NAME" in content
    assert "PRECACHE_ASSETS" in content
    assert "self.addEventListener('fetch'" in content


def test_base_html_pwa_and_social_tags():
    """Verify that base template contains PWA manifest link and OpenGraph tags."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # PWA tags
    assert '<link rel="manifest" href="/manifest.json">' in html
    assert '<meta name="theme-color"' in html
    assert '<meta name="apple-mobile-web-app-capable" content="yes">' in html
    assert 'id="pwa-install-btn"' in html
    assert 'id="offline-toast"' in html
    assert 'id="share-toast"' in html

    # OpenGraph tags
    assert '<meta property="og:site_name" content="AirTrace RU">' in html
    assert '<meta property="og:locale" content="ru_RU">' in html
    assert '<meta property="og:title"' in html
    assert '<meta property="og:description"' in html


def test_city_page_share_buttons_and_dynamic_og():
    """Verify that city page includes share buttons and city-specific OpenGraph tags."""
    response = client.get("/city/moscow")
    assert response.status_code == 200
    html = response.text

    # Dynamic OG tags
    assert "Качество воздуха в г. Москва" in html
    assert '<meta property="og:title"' in html
    assert '<meta property="og:description"' in html

    # Share and Story Card buttons
    assert 'id="city-share-btn"' in html
    assert 'id="city-download-card-btn"' in html
