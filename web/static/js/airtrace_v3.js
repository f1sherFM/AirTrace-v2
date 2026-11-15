/**
 * AirTrace v3 Client Enhancements
 * - Instant City Search & Autocomplete
 * - LocalStorage Favorites System
 * - Pure SVG Interactive Forecast Timeline Chart
 * - Pure SVG History / Trends Chart
 */

(function () {
    'use strict';

    /**
     * Helper to escape HTML characters to prevent XSS vulnerabilities.
     */
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // -------------------------------------------------------------
    // 1. Instant City Search & Autocomplete
    // -------------------------------------------------------------
    function initCitySearch() {
        const input = document.getElementById('global-city-search');
        const resultsBox = document.getElementById('city-search-results');
        if (!input || !resultsBox) return;

        let debounceTimer = null;
        let activeIndex = -1;

        async function fetchSearchResults(query) {
            if (!query || query.trim().length === 0) {
                resultsBox.classList.add('hidden');
                resultsBox.innerHTML = '';
                return;
            }

            try {
                const res = await fetch('/v3/cities?q=' + encodeURIComponent(query.trim()) + '&limit=8');
                if (!res.ok) return;
                const data = await res.json();
                renderResults(data.cities || []);
            } catch (err) {
                console.error('City search failed', err);
            }
        }

        function renderResults(cities) {
            if (!cities || cities.length === 0) {
                resultsBox.innerHTML = '<div class="p-3 text-sm text-white/60 text-center">Город не найден. Нажмите "Свои координаты".</div>';
                resultsBox.classList.remove('hidden');
                return;
            }

            let html = '<div class="py-1">';
            cities.forEach((city, idx) => {
                const escapedName = escapeHtml(city.name);
                const escapedKey = encodeURIComponent(city.key || '');
                const regionStr = city.region ? `<span class="text-xs text-white/50 block">${escapeHtml(city.region)}</span>` : '';
                const majorBadge = city.is_major ? '<span class="text-[10px] bg-teal-500/20 text-teal-300 px-1.5 py-0.5 rounded ml-2">Крупный</span>' : '';
                html += `
                    <a href="/city/${escapedKey}" 
                       data-index="${idx}"
                       class="search-result-item block px-4 py-2.5 hover:bg-white/15 transition-colors border-b border-white/5 last:border-0 flex items-center justify-between">
                        <div>
                            <div class="font-medium text-sm text-white flex items-center">${escapedName} ${majorBadge}</div>
                            ${regionStr}
                        </div>
                        <i data-lucide="arrow-right" class="w-4 h-4 text-white/40"></i>
                    </a>
                `;
            });
            html += '</div>';

            resultsBox.innerHTML = html;
            resultsBox.classList.remove('hidden');
            if (window.lucide) window.lucide.createIcons();
            activeIndex = -1;
        }

        input.addEventListener('input', function (e) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => fetchSearchResults(e.target.value), 180);
        });

        input.addEventListener('focus', function () {
            if (input.value.trim().length > 0) {
                fetchSearchResults(input.value);
            }
        });

        // Keyboard navigation
        input.addEventListener('keydown', function (e) {
            const items = resultsBox.querySelectorAll('.search-result-item');
            if (items.length === 0 || resultsBox.classList.contains('hidden')) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIndex = (activeIndex + 1) % items.length;
                updateActiveItem(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndex = (activeIndex - 1 + items.length) % items.length;
                updateActiveItem(items);
            } else if (e.key === 'Enter') {
                if (activeIndex >= 0 && items[activeIndex]) {
                    e.preventDefault();
                    items[activeIndex].click();
                }
            } else if (e.key === 'Escape') {
                resultsBox.classList.add('hidden');
            }
        });

        function updateActiveItem(items) {
            items.forEach((item, idx) => {
                if (idx === activeIndex) {
                    item.classList.add('bg-white/20');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('bg-white/20');
                }
            });
        }

        // Close on click outside
        document.addEventListener('click', function (e) {
            if (!input.contains(e.target) && !resultsBox.contains(e.target)) {
                resultsBox.classList.add('hidden');
            }
        });
    }

    // -------------------------------------------------------------
    // 2. Favorites System (localStorage)
    // -------------------------------------------------------------
    const FAVORITES_KEY = 'airtrace_v3_favorites';

    function getFavorites() {
        try {
            return JSON.parse(localStorage.getItem(FAVORITES_KEY)) || [
                { key: 'moscow', name: 'Москва' },
                { key: 'spb', name: 'Санкт-Петербург' }
            ];
        } catch {
            return [];
        }
    }

    function saveFavorites(favs) {
        try {
            localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs));
        } catch (e) {
            console.error('Failed to save favorites', e);
        }
    }

    function renderFavoritesBar() {
        const bar = document.getElementById('favorites-bar');
        if (!bar) return;

        const favs = getFavorites();
        if (favs.length === 0) {
            bar.innerHTML = '<span class="text-xs text-white/40 italic">Добавляйте города в избранное звездочкой ⭐</span>';
            return;
        }

        let html = '<div class="flex items-center gap-2 flex-wrap">';
        html += '<span class="text-xs text-white/60 mr-1 flex items-center gap-1"><i data-lucide="star" class="w-3.5 h-3.5 text-amber-300"></i> Избранное:</span>';
        
        favs.forEach(f => {
            const escapedKey = encodeURIComponent(f.key || '');
            const escapedName = escapeHtml(f.name || f.key);
            html += `
                <div class="inline-flex items-center gap-1 bg-white/10 hover:bg-white/20 border border-white/15 rounded-lg px-2.5 py-1 text-xs text-white transition-colors">
                    <a href="/city/${escapedKey}" class="hover:underline">${escapedName}</a>
                    <button type="button" class="remove-fav-btn text-white/40 hover:text-rose-300 ml-1" data-key="${escapedKey}" title="Удалить">✕</button>
                </div>
            `;
        });
        html += '</div>';

        bar.innerHTML = html;
        if (window.lucide) window.lucide.createIcons();

        // Bind remove buttons
        bar.querySelectorAll('.remove-fav-btn').forEach(btn => {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                const key = this.getAttribute('data-key');
                const updated = getFavorites().filter(item => item.key !== key);
                saveFavorites(updated);
                renderFavoritesBar();
                updateCityFavoriteBtn();
                syncAllCardStars();
            });
        });
    }

    function updateStarVisual(btn, isFav) {
        if (isFav) {
            btn.innerHTML = '<i data-lucide="star" class="w-4 h-4 fill-amber-300 text-amber-300"></i>';
            btn.setAttribute('title', 'Удалить из избранного');
        } else {
            btn.innerHTML = '<i data-lucide="star" class="w-4 h-4 text-white/30 hover:text-amber-300"></i>';
            btn.setAttribute('title', 'Добавить в избранное');
        }
        if (window.lucide) window.lucide.createIcons();
    }

    function syncAllCardStars() {
        const favs = getFavorites();
        document.querySelectorAll('.card-fav-star').forEach(btn => {
            const key = btn.getAttribute('data-city-key');
            const isFav = favs.some(f => f.key === key);
            updateStarVisual(btn, isFav);
        });
    }

    function initCardFavoriteButtons() {
        const favs = getFavorites();
        document.querySelectorAll('.card-fav-star').forEach(btn => {
            const key = btn.getAttribute('data-city-key');
            const isFav = favs.some(f => f.key === key);
            updateStarVisual(btn, isFav);

            btn.onclick = function (e) {
                e.preventDefault();
                e.stopPropagation();
                const name = btn.getAttribute('data-city-name');
                let currentFavs = getFavorites();
                const exists = currentFavs.some(f => f.key === key);
                if (exists) {
                    currentFavs = currentFavs.filter(f => f.key !== key);
                } else {
                    currentFavs.push({ key, name });
                }
                saveFavorites(currentFavs);
                updateStarVisual(btn, !exists);
                renderFavoritesBar();
                updateCityFavoriteBtn();
                syncAllCardStars();
            };
        });
    }

    function updateCityFavoriteBtn() {
        const favBtn = document.getElementById('city-fav-toggle-btn');
        if (!favBtn) return;

        const currentKey = favBtn.getAttribute('data-city-key');
        const currentName = favBtn.getAttribute('data-city-name');
        if (!currentKey) return;

        const favs = getFavorites();
        const isFav = favs.some(f => f.key === currentKey);

        if (isFav) {
            favBtn.innerHTML = '<i data-lucide="star" class="w-4 h-4 fill-amber-300 text-amber-300"></i><span>В избранном</span>';
            favBtn.classList.add('bg-amber-500/20', 'border-amber-400/40');
        } else {
            favBtn.innerHTML = '<i data-lucide="star" class="w-4 h-4 text-white/70"></i><span>В избранное</span>';
            favBtn.classList.remove('bg-amber-500/20', 'border-amber-400/40');
        }
        if (window.lucide) window.lucide.createIcons();
    }

    function initFavoriteButton() {
        const favBtn = document.getElementById('city-fav-toggle-btn');
        if (!favBtn) return;

        favBtn.addEventListener('click', function () {
            const currentKey = favBtn.getAttribute('data-city-key');
            const currentName = favBtn.getAttribute('data-city-name');
            if (!currentKey) return;

            let favs = getFavorites();
            const exists = favs.some(f => f.key === currentKey);

            if (exists) {
                favs = favs.filter(f => f.key !== currentKey);
            } else {
                favs.push({ key: currentKey, name: currentName });
            }
            saveFavorites(favs);
            updateCityFavoriteBtn();
            renderFavoritesBar();
        });

        updateCityFavoriteBtn();
    }

    // -------------------------------------------------------------
    // 3. Pure SVG Interactive Forecast Timeline Chart
    // -------------------------------------------------------------
    function renderForecastChart() {
        const container = document.getElementById('forecast-chart-container');
        if (!container || !window.FORECAST_DATA || window.FORECAST_DATA.length === 0) return;

        const data = window.FORECAST_DATA;
        const width = container.clientWidth || 700;
        const height = 220;
        const padLeft = 40;
        const padRight = 20;
        const padTop = 30;
        const padBottom = 35;
        const chartW = width - padLeft - padRight;
        const chartH = height - padTop - padBottom;

        const aqiValues = data.map(d => d.aqi || 0);
        const maxVal = Math.max(160, Math.ceil(Math.max(...aqiValues) / 50) * 50);

        function getX(idx) {
            return padLeft + (idx / (data.length - 1)) * chartW;
        }

        function getY(val) {
            return padTop + (1 - (val / maxVal)) * chartH;
        }

        function getAqiColor(val) {
            if (val <= 50) return '#10B981';
            if (val <= 100) return '#F59E0B';
            if (val <= 150) return '#F97316';
            if (val <= 200) return '#EF4444';
            return '#8B5CF6';
        }

        // Generate points for the smooth line
        let points = [];
        data.forEach((d, idx) => {
            points.push({ x: getX(idx), y: getY(d.aqi), aqi: d.aqi, time: d.time, pm25: d.pm25, cat: d.category });
        });

        let pathD = `M ${points[0].x} ${points[0].y}`;
        for (let i = 1; i < points.length; i++) {
            const prev = points[i - 1];
            const curr = points[i];
            const midX = (prev.x + curr.x) / 2;
            pathD += ` C ${midX} ${prev.y}, ${midX} ${curr.y}, ${curr.x} ${curr.y}`;
        }

        let areaD = `${pathD} L ${points[points.length - 1].x} ${height - padBottom} L ${points[0].x} ${height - padBottom} Z`;

        // Safety Threshold Lines
        const thresholds = [
            { val: 50, label: '50 Хорошо', color: 'rgba(16, 185, 129, 0.35)' },
            { val: 100, label: '100 Умеренно', color: 'rgba(245, 158, 11, 0.35)' },
            { val: 150, label: '150 Вредно', color: 'rgba(249, 115, 22, 0.35)' }
        ];

        let thresholdLines = '';
        thresholds.forEach(t => {
            if (t.val <= maxVal) {
                const y = getY(t.val);
                thresholdLines += `
                    <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="${t.color}" stroke-dasharray="4 4" stroke-width="1" />
                    <text x="${padLeft + 4}" y="${y - 4}" fill="rgba(255,255,255,0.4)" font-size="9">${t.label}</text>
                `;
            }
        });

        // X Axis Time Labels (every 4-6 points)
        const step = Math.max(1, Math.floor(data.length / 6));
        let xLabels = '';
        for (let i = 0; i < data.length; i += step) {
            const pt = points[i];
            xLabels += `
                <text x="${pt.x}" y="${height - 12}" fill="rgba(255,255,255,0.6)" font-size="11" text-anchor="middle">${pt.time}</text>
                <line x1="${pt.x}" y1="${height - padBottom}" x2="${pt.x}" y2="${height - padBottom + 4}" stroke="rgba(255,255,255,0.2)" />
            `;
        }

        // SVG string
        const svg = `
            <svg viewBox="0 0 ${width} ${height}" class="w-full h-auto overflow-visible select-none" id="forecast-svg">
                <defs>
                    <linearGradient id="forecastAreaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.35" />
                        <stop offset="100%" stop-color="#38BDF8" stop-opacity="0.0" />
                    </linearGradient>
                </defs>
                ${thresholdLines}
                <path d="${areaD}" fill="url(#forecastAreaGrad)" />
                <path d="${pathD}" fill="none" stroke="#38BDF8" stroke-width="3" stroke-linecap="round" />
                ${points.map((p, idx) => `
                    <circle cx="${p.x}" cy="${p.y}" r="4" fill="${getAqiColor(p.aqi)}" stroke="#0f172a" stroke-width="2" class="cursor-pointer hover:r-6 transition-all" data-idx="${idx}" />
                `).join('')}
                ${xLabels}
                <!-- Hover guide line -->
                <line id="hover-line" x1="0" y1="${padTop}" x2="0" y2="${height - padBottom}" stroke="rgba(255,255,255,0.5)" stroke-width="1" stroke-dasharray="3 3" style="display:none;" />
            </svg>
            <div id="chart-tooltip" class="absolute hidden bg-slate-900/95 border border-white/20 backdrop-blur-md rounded-xl p-3 text-xs pointer-events-none shadow-2xl z-50"></div>
        `;

        container.innerHTML = svg;

        // Tooltip interactivity
        const svgElem = document.getElementById('forecast-svg');
        const tooltip = document.getElementById('chart-tooltip');
        const hoverLine = document.getElementById('hover-line');

        svgElem.addEventListener('mousemove', function (e) {
            const rect = svgElem.getBoundingClientRect();
            const mouseX = ((e.clientX - rect.left) / rect.width) * width;

            // Find closest point
            let closest = null;
            let minDist = Infinity;
            points.forEach(pt => {
                const dist = Math.abs(pt.x - mouseX);
                if (dist < minDist) {
                    minDist = dist;
                    closest = pt;
                }
            });

            if (closest && minDist < (chartW / (data.length - 1)) * 1.5) {
                hoverLine.setAttribute('x1', closest.x);
                hoverLine.setAttribute('x2', closest.x);
                hoverLine.style.display = 'block';

                tooltip.innerHTML = `
                    <div class="font-semibold text-white mb-1">${closest.time}</div>
                    <div class="flex items-center gap-2 mb-1">
                        <span class="w-2.5 h-2.5 rounded-full" style="background:${getAqiColor(closest.aqi)}"></span>
                        <span class="text-sm font-bold text-white">AQI ${closest.aqi}</span>
                        <span class="text-white/70">(${closest.cat})</span>
                    </div>
                    <div class="text-white/60">PM2.5: ${closest.pm25 !== null ? closest.pm25 + ' мкг/м³' : '--'}</div>
                `;

                const toolX = (closest.x / width) * rect.width;
                const toolY = (closest.y / height) * rect.height;
                tooltip.style.left = `${Math.min(rect.width - 140, Math.max(10, toolX - 60))}px`;
                tooltip.style.top = `${Math.max(10, toolY - 70)}px`;
                tooltip.classList.remove('hidden');
            } else {
                hoverLine.style.display = 'none';
                tooltip.classList.add('hidden');
            }
        });

        svgElem.addEventListener('mouseleave', function () {
            hoverLine.style.display = 'none';
            tooltip.classList.add('hidden');
        });
    }

    // -------------------------------------------------------------
    // 4. Pure SVG Trends / History Chart
    // -------------------------------------------------------------
    function renderTrendsChart() {
        const container = document.getElementById('trends-chart-container');
        if (!container || !window.TRENDS_DATA || window.TRENDS_DATA.length < 2) return;

        const data = window.TRENDS_DATA;
        const width = container.clientWidth || 700;
        const height = 200;
        const padLeft = 40;
        const padRight = 20;
        const padTop = 25;
        const padBottom = 35;
        const chartW = width - padLeft - padRight;
        const chartH = height - padTop - padBottom;

        const maxAqi = Math.max(100, Math.ceil(Math.max(...data.map(d => d.aqi_max || d.aqi || 50)) / 25) * 25);

        function getX(idx) { return padLeft + (idx / (data.length - 1)) * chartW; }
        function getY(val) { return padTop + (1 - (val / maxAqi)) * chartH; }

        let avgPoints = data.map((d, i) => ({ x: getX(i), y: getY(d.aqi_avg || d.aqi), val: d.aqi_avg || d.aqi, label: d.label }));
        let pathD = `M ${avgPoints[0].x} ${avgPoints[0].y}`;
        for (let i = 1; i < avgPoints.length; i++) {
            const prev = avgPoints[i - 1];
            const curr = avgPoints[i];
            const midX = (prev.x + curr.x) / 2;
            pathD += ` C ${midX} ${prev.y}, ${midX} ${curr.y}, ${curr.x} ${curr.y}`;
        }

        let bars = '';
        data.forEach((d, i) => {
            const x = getX(i);
            const yMin = getY(d.aqi_min || d.aqi);
            const yMax = getY(d.aqi_max || d.aqi);
            bars += `
                <line x1="${x}" y1="${yMin}" x2="${x}" y2="${yMax}" stroke="rgba(56, 189, 248, 0.4)" stroke-width="4" stroke-linecap="round" />
                <circle cx="${x}" cy="${getY(d.aqi_avg || d.aqi)}" r="4.5" fill="#38BDF8" />
                <text x="${x}" y="${height - 12}" fill="rgba(255,255,255,0.6)" font-size="10" text-anchor="middle">${d.label}</text>
            `;
        });

        container.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" class="w-full h-auto overflow-visible select-none">
                <line x1="${padLeft}" y1="${getY(50)}" x2="${width - padRight}" y2="${getY(50)}" stroke="rgba(16, 185, 129, 0.3)" stroke-dasharray="4 4" />
                <line x1="${padLeft}" y1="${getY(100)}" x2="${width - padRight}" y2="${getY(100)}" stroke="rgba(245, 158, 11, 0.3)" stroke-dasharray="4 4" />
                <path d="${pathD}" fill="none" stroke="#38BDF8" stroke-width="2.5" />
                ${bars}
            </svg>
        `;
    }

    // -------------------------------------------------------------
    // 5. Client-side Visited Cities Storage & Catalog Card Hydration
    // -------------------------------------------------------------
    function saveCurrentCityVisit() {
        const meta = document.getElementById('city-meta');
        if (!meta) return;
        const key = meta.dataset.cityKey;
        if (!key) return;
        const aqi = parseInt(meta.dataset.aqi, 10);
        if (isNaN(aqi)) return;
        const category = meta.dataset.category || 'Хорошо';
        const color = meta.dataset.color || '#10b981';
        const name = meta.dataset.cityName || key;
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const nowMs = Date.now();
        const MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours
        const MAX_ENTRIES = 50;

        try {
            const raw = localStorage.getItem('airtrace_city_visits');
            let visits = raw ? JSON.parse(raw) : {};
            if (typeof visits !== 'object' || visits === null || Array.isArray(visits)) {
                visits = {};
            }

            // Evict visits older than 24h
            const filteredEntries = Object.entries(visits).filter(([_, item]) => {
                return item && typeof item === 'object' && (nowMs - (item.timestamp || 0) < MAX_AGE_MS);
            });

            // Evict oldest if exceeding max entries limit
            filteredEntries.sort((a, b) => (b[1].timestamp || 0) - (a[1].timestamp || 0));
            const trimmed = Object.fromEntries(filteredEntries.slice(0, MAX_ENTRIES - 1));

            trimmed[key] = {
                key: key,
                name: name,
                aqi: aqi,
                category: category,
                color: color,
                time: timeStr,
                timestamp: nowMs
            };
            localStorage.setItem('airtrace_city_visits', JSON.stringify(trimmed));
        } catch (e) {
            console.error('Failed to save city visit', e);
        }
    }

    function hydrateCatalogCardsFromLocalStorage() {
        const cards = document.querySelectorAll('.city-catalog-card');
        if (!cards || cards.length === 0) return;

        let visits = {};
        try {
            const raw = localStorage.getItem('airtrace_city_visits');
            if (raw) visits = JSON.parse(raw);
        } catch (e) {
            return;
        }

        cards.forEach(function (card) {
            const key = card.dataset.cityKey;
            const visit = visits[key];
            if (visit && visit.aqi !== undefined) {
                const statusSlot = card.querySelector('.city-status-slot');
                const aqiSlot = card.querySelector('.city-aqi-badge-slot');
                const escapedColor = escapeHtml(visit.color || '#10b981');
                const escapedCategory = escapeHtml(visit.category || 'Хорошо');
                const escapedTime = escapeHtml(visit.time || '');
                const safeAqi = parseInt(visit.aqi, 10) || 0;

                if (statusSlot) {
                    statusSlot.innerHTML = `
                        <span class="text-[11px] px-2 py-0.5 rounded-md font-medium flex items-center gap-1.5 w-fit shadow-sm" style="background-color: ${escapedColor}25; border: 1px solid ${escapedColor}55; color: #ffffff;">
                            <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${escapedColor}"></span>
                            <span>AQI ${safeAqi} • ${escapedCategory} (${escapedTime})</span>
                        </span>
                    `;
                }

                if (aqiSlot) {
                    const existingBtn = aqiSlot.querySelector('.card-fav-star');
                    const btnHtml = existingBtn ? existingBtn.outerHTML : '';
                    aqiSlot.innerHTML = `
                        <span class="text-xl font-black tracking-tight" style="color: ${escapedColor}">${safeAqi}</span>
                        ${btnHtml}
                        <i data-lucide="arrow-up-right" class="w-4 h-4 opacity-70 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all text-teal-300"></i>
                    `;
                }
            }
        });

        initCardFavoriteButtons();

        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    // -------------------------------------------------------------
    // 6. Interactive Air Quality Map (AirTrace v3.1 Feature)
    // -------------------------------------------------------------
    let leafletMapInstance = null;
    let mapMarkerLayer = null;

    function initInteractiveMap() {
        const mapContainer = document.getElementById('airtrace-russia-map');
        const dataScript = document.getElementById('cities-map-data');
        if (!mapContainer || !dataScript) return;

        let cities = [];
        try {
            cities = JSON.parse(dataScript.textContent);
        } catch (e) {
            console.error('Failed to parse cities map data', e);
            return;
        }

        const gridBtn = document.getElementById('catalog-view-grid-btn');
        const mapBtn = document.getElementById('catalog-view-map-btn');
        const gridWrapper = document.getElementById('catalog-grid-wrapper');
        const mapWrapper = document.getElementById('catalog-map-wrapper');
        const resetBoundsBtn = document.getElementById('map-reset-bounds-btn');
        const filterChips = document.querySelectorAll('.map-filter-chip');

        function setViewMode(mode) {
            if (mode === 'map') {
                if (gridWrapper) gridWrapper.classList.add('hidden');
                if (mapWrapper) mapWrapper.classList.remove('hidden');
                if (mapBtn) {
                    mapBtn.classList.add('bg-white/20', 'text-white', 'shadow-sm');
                    mapBtn.classList.remove('text-white/70');
                    mapBtn.setAttribute('aria-selected', 'true');
                }
                if (gridBtn) {
                    gridBtn.classList.remove('bg-white/20', 'text-white', 'shadow-sm');
                    gridBtn.classList.add('text-white/70');
                    gridBtn.setAttribute('aria-selected', 'false');
                }
                localStorage.setItem('airtrace_catalog_view', 'map');

                if (!leafletMapInstance) {
                    setupMap();
                } else {
                    setTimeout(() => {
                        leafletMapInstance.invalidateSize();
                    }, 120);
                }
            } else {
                if (mapWrapper) mapWrapper.classList.add('hidden');
                if (gridWrapper) gridWrapper.classList.remove('hidden');
                if (gridBtn) {
                    gridBtn.classList.add('bg-white/20', 'text-white', 'shadow-sm');
                    gridBtn.classList.remove('text-white/70');
                    gridBtn.setAttribute('aria-selected', 'true');
                }
                if (mapBtn) {
                    mapBtn.classList.remove('bg-white/20', 'text-white', 'shadow-sm');
                    mapBtn.classList.add('text-white/70');
                    mapBtn.setAttribute('aria-selected', 'false');
                }
                localStorage.setItem('airtrace_catalog_view', 'grid');
            }
        }

        if (gridBtn && mapBtn) {
            gridBtn.addEventListener('click', () => setViewMode('grid'));
            mapBtn.addEventListener('click', () => setViewMode('map'));
        }

        // Restore saved view preference
        const savedView = localStorage.getItem('airtrace_catalog_view');
        if (savedView === 'map') {
            setViewMode('map');
        }

        function setupMap() {
            if (typeof L === 'undefined') {
                mapContainer.innerHTML = '<div class="p-8 text-center text-sm text-white/60">Загрузка картографического движка...</div>';
                return;
            }

            mapContainer.innerHTML = '';

            leafletMapInstance = L.map('airtrace-russia-map', {
                center: [61.5, 90.0],
                zoom: 3,
                minZoom: 2,
                maxZoom: 14,
                zoomControl: true,
                attributionControl: false
            });

            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(leafletMapInstance);

            mapMarkerLayer = L.layerGroup().addTo(leafletMapInstance);

            renderMapMarkers('all');

            if (resetBoundsBtn) {
                resetBoundsBtn.addEventListener('click', () => {
                    if (leafletMapInstance) {
                        leafletMapInstance.setView([61.5, 90.0], 3);
                    }
                });
            }

            filterChips.forEach(chip => {
                chip.addEventListener('click', function () {
                    filterChips.forEach(c => {
                        c.classList.remove('active', 'bg-teal-500/30', 'text-teal-200', 'border-teal-400/40');
                        c.classList.add('bg-white/10', 'text-white/80', 'border-white/10');
                    });
                    this.classList.add('active', 'bg-teal-500/30', 'text-teal-200', 'border-teal-400/40');
                    this.classList.remove('bg-white/10', 'text-white/80', 'border-white/10');
                    const filter = this.getAttribute('data-filter') || 'all';
                    renderMapMarkers(filter);
                });
            });
        }

        function renderMapMarkers(filter) {
            if (!mapMarkerLayer || !leafletMapInstance) return;
            mapMarkerLayer.clearLayers();

            const favs = getFavorites();
            let visits = {};
            try {
                const raw = localStorage.getItem('airtrace_city_visits');
                if (raw) visits = JSON.parse(raw);
            } catch (e) {}

            cities.forEach(city => {
                const isFav = favs.some(f => f.key === city.key);
                const visit = visits[city.key];

                if (filter === 'major' && !city.is_major) return;
                if (filter === 'favorites' && !isFav) return;
                if (filter === 'attention') {
                    const hasHighAqi = visit && visit.aqi > 50;
                    if (!hasHighAqi) return;
                }

                let color = '#38bdf8';
                let displayAqi = '•';
                let hasRealReading = false;
                let category = 'Требует замера';

                if (visit && visit.aqi !== undefined) {
                    hasRealReading = true;
                    color = visit.color || (visit.aqi <= 50 ? '#10b981' : visit.aqi <= 100 ? '#f59e0b' : visit.aqi <= 150 ? '#f97316' : '#ef4444');
                    displayAqi = String(visit.aqi);
                    category = visit.category || 'Замер выполнен';
                }

                const markerSize = hasRealReading ? 32 : (city.is_major ? 26 : 20);
                const pulseRing = city.is_major ? `<div class="pulse-ring" style="border: 2px solid ${color};"></div>` : '';

                const iconHtml = `
                    <div class="map-marker-pin relative flex items-center justify-center cursor-pointer select-none" style="width: ${markerSize}px; height: ${markerSize}px;">
                        ${pulseRing}
                        <div class="w-full h-full rounded-full flex items-center justify-center font-black shadow-lg text-white text-[11px] border border-white/30" style="background-color: ${color};">
                            ${displayAqi}
                        </div>
                    </div>
                `;

                const customIcon = L.divIcon({
                    html: iconHtml,
                    className: 'custom-city-marker',
                    iconSize: [markerSize, markerSize],
                    iconAnchor: [markerSize / 2, markerSize / 2],
                    popupAnchor: [0, -markerSize / 2]
                });

                const escapedName = escapeHtml(city.name);
                const escapedRegion = escapeHtml(city.region || '');
                const escapedKey = encodeURIComponent(city.key);
                const escapedCategory = escapeHtml(category);

                const statusBadge = hasRealReading
                    ? `<span class="text-xs px-2 py-0.5 rounded-full font-bold" style="background-color: ${color}25; color: ${color}; border: 1px solid ${color}55;">AQI ${displayAqi} • ${escapedCategory}</span>`
                    : `<span class="text-[11px] px-2 py-0.5 rounded-full bg-white/10 text-white/60 border border-white/10">Требует замера</span>`;

                const popupContent = `
                    <div class="p-4 space-y-2.5 min-w-[220px]">
                        <div class="flex items-start justify-between gap-2">
                            <div>
                                <div class="font-bold text-base text-white flex items-center gap-1.5">
                                    <span>${escapedName}</span>
                                    ${city.is_major ? '<span class="text-[9px] bg-teal-500/20 text-teal-300 px-1 py-0.2 rounded font-semibold">Крупный</span>' : ''}
                                </div>
                                <div class="text-xs text-white/60">${escapedRegion}</div>
                            </div>
                        </div>

                        <div class="pt-1">
                            ${statusBadge}
                        </div>

                        <div class="pt-2 border-t border-white/10 flex items-center justify-between gap-2">
                            <a href="/city/${escapedKey}" class="text-xs font-semibold text-teal-300 hover:text-teal-200 hover:underline flex items-center gap-1">
                                <span>Открыть прогноз</span>
                                <span>→</span>
                            </a>
                            <button type="button" class="map-popup-fav-btn p-1 rounded hover:bg-white/10 text-xs text-white/50 hover:text-amber-300" data-key="${escapedKey}" data-name="${escapedName}" title="В избранное">
                                <i data-lucide="star" class="w-3.5 h-3.5 ${isFav ? 'fill-amber-300 text-amber-300' : ''}"></i>
                            </button>
                        </div>
                    </div>
                `;

                const marker = L.marker([city.lat, city.lon], { icon: customIcon });
                marker.bindPopup(popupContent);
                marker.on('popupopen', () => {
                    if (window.lucide) window.lucide.createIcons();
                    const popupEl = marker.getPopup().getElement();
                    if (popupEl) {
                        const btn = popupEl.querySelector('.map-popup-fav-btn');
                        if (btn) {
                            btn.onclick = function (e) {
                                e.stopPropagation();
                                const currentFavs = getFavorites();
                                const exists = currentFavs.some(f => f.key === city.key);
                                let updated;
                                if (exists) {
                                    updated = currentFavs.filter(f => f.key !== city.key);
                                } else {
                                    updated = [...currentFavs, { key: city.key, name: city.name }];
                                }
                                saveFavorites(updated);
                                renderFavoritesBar();
                                syncAllCardStars();
                                renderMapMarkers(filter);
                            };
                        }
                    }
                });

                mapMarkerLayer.addLayer(marker);
            });
        }
    }

    // -------------------------------------------------------------
    // 7. Multi-City Comparison & Multiline Chart (AirTrace v3.2 Feature)
    // -------------------------------------------------------------
    function initComparePage() {
        const chartContainer = document.getElementById('compare-multiline-chart');
        const forecastScript = document.getElementById('compare-forecast-data');
        const allCitiesScript = document.getElementById('compare-all-cities-data');
        const searchInput = document.getElementById('compare-search-input');
        const autocompleteBox = document.getElementById('compare-autocomplete-box');
        const hiddenCitiesInput = document.getElementById('compare-cities-hidden');
        const removeButtons = document.querySelectorAll('.remove-compare-city-btn');

        // Handle city removal
        removeButtons.forEach(btn => {
            btn.addEventListener('click', function () {
                const keyToRemove = this.getAttribute('data-key');
                const currentStr = hiddenCitiesInput ? hiddenCitiesInput.value : '';
                const updatedList = currentStr.split(',').map(s => s.trim()).filter(s => s && s !== keyToRemove);
                if (updatedList.length > 0) {
                    window.location.href = '/compare?cities=' + encodeURIComponent(updatedList.join(','));
                }
            });
        });

        // City Search Autocomplete for adding to compare
        if (searchInput && autocompleteBox && allCitiesScript) {
            let allCities = [];
            try {
                allCities = JSON.parse(allCitiesScript.textContent);
            } catch (e) {}

            searchInput.addEventListener('input', function (e) {
                const q = e.target.value.trim().toLowerCase();
                if (!q) {
                    autocompleteBox.classList.add('hidden');
                    autocompleteBox.innerHTML = '';
                    return;
                }

                const currentCities = hiddenCitiesInput ? hiddenCitiesInput.value.split(',').map(s => s.trim().toLowerCase()) : [];
                const matches = allCities.filter(c => {
                    if (currentCities.includes(c.key.toLowerCase())) return false;
                    const name = c.name.toLowerCase();
                    const key = c.key.toLowerCase();
                    return name.includes(q) || key.includes(q);
                }).slice(0, 6);

                if (matches.length === 0) {
                    autocompleteBox.innerHTML = '<div class="p-3 text-xs text-white/60 text-center">Город не найден или уже добавлен</div>';
                    autocompleteBox.classList.remove('hidden');
                    return;
                }

                let html = '<div class="py-1">';
                matches.forEach(c => {
                    const escapedName = escapeHtml(c.name);
                    const escapedRegion = escapeHtml(c.region || '');
                    html += `
                        <div class="compare-suggest-item px-4 py-2 hover:bg-white/15 cursor-pointer flex items-center justify-between transition-colors border-b border-white/5 last:border-0" data-key="${c.key}">
                            <div>
                                <span class="text-xs font-semibold text-white">${escapedName}</span>
                                <span class="text-[10px] text-white/50 block">${escapedRegion}</span>
                            </div>
                            <span class="text-[10px] text-teal-300 font-bold">+ Добавить</span>
                        </div>
                    `;
                });
                html += '</div>';

                autocompleteBox.innerHTML = html;
                autocompleteBox.classList.remove('hidden');

                autocompleteBox.querySelectorAll('.compare-suggest-item').forEach(item => {
                    item.addEventListener('click', function () {
                        const newKey = this.getAttribute('data-key');
                        const nextList = [...currentCities, newKey].slice(0, 4);
                        window.location.href = '/compare?cities=' + encodeURIComponent(nextList.join(','));
                    });
                });
            });

            document.addEventListener('click', function (e) {
                if (!searchInput.contains(e.target) && !autocompleteBox.contains(e.target)) {
                    autocompleteBox.classList.add('hidden');
                }
            });
        }

        // Render Multi-line Chart
        if (!chartContainer || !forecastScript) return;
        let seriesData = [];
        try {
            seriesData = JSON.parse(forecastScript.textContent);
        } catch (e) {
            console.error('Failed to parse compare forecast data', e);
            return;
        }

        if (!seriesData || seriesData.length === 0) return;

        const maxLenSeries = seriesData.reduce((prev, curr) => {
            const prevLen = (prev && prev.points) ? prev.points.length : 0;
            const currLen = (curr && curr.points) ? curr.points.length : 0;
            return currLen > prevLen ? curr : prev;
        }, seriesData[0]);

        if (!maxLenSeries || !maxLenSeries.points || maxLenSeries.points.length === 0) {
            chartContainer.innerHTML = '<div class="p-6 text-center text-xs opacity-60">Данные прогноза формируются</div>';
            return;
        }

        const width = 900;
        const height = 280;
        const padLeft = 45;
        const padRight = 20;
        const padTop = 30;
        const padBottom = 40;

        let maxAqi = 100;
        seriesData.forEach(s => {
            if (s.points) {
                s.points.forEach(p => {
                    if (p.aqi > maxAqi) maxAqi = p.aqi;
                });
            }
        });
        maxAqi = Math.ceil((maxAqi + 15) / 50) * 50;

        const numPoints = maxLenSeries.points.length;
        const getX = (idx) => padLeft + (idx / Math.max(numPoints - 1, 1)) * (width - padLeft - padRight);
        const getY = (val) => padTop + (height - padTop - padBottom) * (1 - (val / maxAqi));

        let svgHtml = `
            <svg viewBox="0 0 ${width} ${height}" class="w-full h-auto overflow-visible select-none font-sans">
                <!-- Grid Lines -->
                <line x1="${padLeft}" y1="${getY(50)}" x2="${width - padRight}" y2="${getY(50)}" stroke="rgba(16, 185, 129, 0.25)" stroke-dasharray="4 4" />
                <text x="${padLeft - 6}" y="${getY(50) + 4}" font-size="10" fill="#10b981" opacity="0.8" text-anchor="end">50</text>

                <line x1="${padLeft}" y1="${getY(100)}" x2="${width - padRight}" y2="${getY(100)}" stroke="rgba(245, 158, 11, 0.25)" stroke-dasharray="4 4" />
                <text x="${padLeft - 6}" y="${getY(100) + 4}" font-size="10" fill="#f59e0b" opacity="0.8" text-anchor="end">100</text>
        `;

        if (maxAqi >= 150) {
            svgHtml += `
                <line x1="${padLeft}" y1="${getY(150)}" x2="${width - padRight}" y2="${getY(150)}" stroke="rgba(239, 68, 68, 0.25)" stroke-dasharray="4 4" />
                <text x="${padLeft - 6}" y="${getY(150) + 4}" font-size="10" fill="#ef4444" opacity="0.8" text-anchor="end">150</text>
            `;
        }

        // Draw Series Lines and Dots
        seriesData.forEach(s => {
            if (!s.points || s.points.length === 0) return;
            let pathD = '';
            s.points.forEach((p, i) => {
                const x = getX(i);
                const y = getY(p.aqi);
                if (i === 0) pathD += `M ${x} ${y}`;
                else pathD += ` L ${x} ${y}`;
            });

            svgHtml += `
                <path d="${pathD}" fill="none" stroke="${s.color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.9" />
            `;

            // Draw points
            s.points.forEach((p, i) => {
                if (i % 3 === 0 || i === s.points.length - 1) {
                    const x = getX(i);
                    const y = getY(p.aqi);
                    svgHtml += `
                        <circle cx="${x}" cy="${y}" r="3.5" fill="${s.color}" stroke="#0b1220" stroke-width="1.5" />
                    `;
                }
            });
        });

        // X-axis Time Labels
        maxLenSeries.points.forEach((p, i) => {
            if (i % 3 === 0 || i === maxLenSeries.points.length - 1) {
                const x = getX(i);
                const timeLabel = p.time || `${i}:00`;
                svgHtml += `
                    <text x="${x}" y="${height - 12}" font-size="10" fill="rgba(255,255,255,0.5)" text-anchor="middle">${timeLabel}</text>
                `;
            }
        });

        svgHtml += `</svg>`;
        chartContainer.innerHTML = svgHtml;
    }

    // Unified initialization on DOM ready
    function init() {
        initCitySearch();
        renderFavoritesBar();
        initFavoriteButton();
        renderForecastChart();
        renderTrendsChart();
        saveCurrentCityVisit();
        hydrateCatalogCardsFromLocalStorage();
        initCardFavoriteButtons();
        initInteractiveMap();
        initComparePage();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Re-render charts on window resize
    let resizeTimer = null;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            renderForecastChart();
            renderTrendsChart();
            initComparePage();
        }, 200);
    });
})();
