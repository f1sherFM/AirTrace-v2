# AirTrace v3 Release & Architecture Specification

## Overview

AirTrace v3 is a major evolutionary milestone for the platform, turning a raw data and alert monitoring tool into a comprehensive, citizen-friendly air quality intelligence ecosystem for Russian cities.

While AirTrace v2 established a robust modular monolith and persistence foundation, v3 focuses on:
1. **User Experience & Visual Analytics**: Interactive SVG timelines, intuitive AQI danger zones, and actionable advice.
2. **City Coverage & Discovery**: Expansion from 9 hardcoded cities to 75+ major Russian industrial, regional, and population centers, with instant fuzzy search and Latin/Cyrillic transliteration.
3. **Domain Lifestyle & Health Advisory Engine**: Direct translation of raw PM2.5/AQI numbers and NMU alerts into 5 tangible daily guidelines (outdoor sports, window ventilation, masks/respirators, HEPA air purifiers, and sensitive group precautions).
4. **National Comparative Analytics**: National air quality leaderboard and rankings (cleanest cities vs pollution watch zones).
5. **Modern API v3 Contract**: Ergonomic endpoints with city-name resolution (`GET /v3/current?city=kazan`), pre-calculated forecast peaks, and backward compatibility with v1 and v2.

---

## What AirTrace v3 Delivers

### 1. Domain Lifestyle & Health Advisory Engine (`domain/advisory/`)
Raw AQI numbers (e.g. `AQI 85`) often lack meaning for everyday users. AirTrace v3 introduces a domain engine that computes practical guidance based on Russian SanPiN and WHO air quality guidelines:
- **Спорт на улице (Outdoor Sports)**: Advice on running, cycling, and workouts. Recommends moving indoors or adjusting intensity when PM2.5 and AQI rise.
- **Проветривание (Ventilation)**: Advises when to ventilate freely, when to do short micro-ventilation, and when to seal windows during NMU smog traps.
- **Защитная маска (Mask Protection)**: Distinguishes between normal air, sensitive group warnings, and mandatory FFP2/FFP3 particulate respirator recommendations.
- **Очиститель воздуха (Air Purifier)**: Advises on HEPA filter intensity, indoor microclimate, and humidity.
- **Чувствительные группы (Sensitive Groups)**: Explicit medical and preventive advisories for children, elderly individuals, pregnant women, and people with respiratory/cardiovascular diseases.

### 2. Expanded Russian City Catalog & Smart Discovery (`application/queries/cities.py`)
- Centralized catalog in `config/cities.yaml` expanded to 75+ cities across all federal districts (Central, North-West, Volga, Ural, Siberia, Far East, South, North Caucasus).
- Instant fuzzy search supporting Russian names, English transliteration (e.g. `krasnoyarsk` -> `Красноярск`), and administrative regions (e.g. `Татарстан` -> `Казань`).
- Direct coordinate resolution: users can query `/v3/current?city=sochi` without knowing exact latitude and longitude.

### 3. National Air Quality Ranking (`application/queries/ranking.py`)
- Computes national average AQI across Russian regions.
- Highlights Top Cleanest Cities and Attention Needed / NMU Alert Zones.
- Exposed via public endpoint `GET /v3/cities/ranking` and rendered directly on the homepage.

### 4. Visual Interactive Charts (`web/static/js/airtrace_v3.js`)
- Replaces raw text card lists with a pure SVG interactive timeline chart:
  - Color-coded safety zones (Green 0-50, Yellow 51-100, Orange 101-150, Red >150).
  - Hover tooltips displaying exact time, AQI, category, and PM2.5 concentrations.
  - Zero external JavaScript dependencies (lightweight vanilla JS, no heavy CDN dependencies, works offline).

### 5. LocalStorage Favorites System
- Users can star any city with the ⭐️ button.
- Saved favorites appear as quick-access chips in the global header for one-click switching.

### 6. Public API v3 (`api/v3/`)
- `GET /v3/cities`: Search and list cities with region metadata.
- `GET /v3/cities/ranking`: National comparative overview.
- `GET /v3/activities/advice`: Structured activity and health recommendations.
- `GET /v3/current`: Current air quality with advisory and city details (supports `?city=...` and `?lat=...&lon=...`).
- `GET /v3/forecast`: Forecast with automated peak analysis (`summary.peak_aqi`, `summary.safest_hour`, `summary.trend`).
- `GET /v3/history`: Historical data queries.
- `GET /v3/trends`: Daily aggregated trends.
- `GET /v3/health`: System and dependency health probes.

---

## Backward Compatibility & Safety

- All `v1` legacy routes (`/weather/current`, `/weather/forecast`, `/history`) remain intact.
- All `v2` public routes (`/v2/current`, `/v2/forecast`, `/v2/history`, `/v2/trends`, `/v2/alerts`) remain 100% backward-compatible.
- Legacy regression test packs, OpenAPI snapshot checks, and SSR smoke tests continue to pass with zero regressions.
