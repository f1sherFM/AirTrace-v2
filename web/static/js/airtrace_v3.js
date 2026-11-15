/**
 * AirTrace v3 Client Enhancements
 * - Instant City Search & Autocomplete
 * - LocalStorage Favorites System
 * - Pure SVG Interactive Forecast Timeline Chart
 * - Pure SVG History / Trends Chart
 */

(function () {
    'use strict';

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
                const regionStr = city.region ? `<span class="text-xs text-white/50 block">${city.region}</span>` : '';
                const majorBadge = city.is_major ? '<span class="text-[10px] bg-teal-500/20 text-teal-300 px-1.5 py-0.5 rounded ml-2">Крупный</span>' : '';
                html += `
                    <a href="/city/${city.key}" 
                       data-index="${idx}"
                       class="search-result-item block px-4 py-2.5 hover:bg-white/15 transition-colors border-b border-white/5 last:border-0 flex items-center justify-between">
                        <div>
                            <div class="font-medium text-sm text-white flex items-center">${city.name} ${majorBadge}</div>
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
            html += `
                <div class="inline-flex items-center gap-1 bg-white/10 hover:bg-white/20 border border-white/15 rounded-lg px-2.5 py-1 text-xs text-white transition-colors">
                    <a href="/city/${f.key}" class="hover:underline">${f.name}</a>
                    <button type="button" class="remove-fav-btn text-white/40 hover:text-rose-300 ml-1" data-key="${f.key}" title="Удалить">✕</button>
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

        try {
            const raw = localStorage.getItem('airtrace_city_visits');
            const visits = raw ? JSON.parse(raw) : {};
            visits[key] = {
                key: key,
                name: name,
                aqi: aqi,
                category: category,
                color: color,
                time: timeStr,
                timestamp: Date.now()
            };
            localStorage.setItem('airtrace_city_visits', JSON.stringify(visits));
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

                if (statusSlot) {
                    statusSlot.innerHTML = `
                        <span class="text-[11px] px-2 py-0.5 rounded-md font-medium flex items-center gap-1.5 w-fit shadow-sm" style="background-color: ${visit.color}25; border: 1px solid ${visit.color}55; color: #ffffff;">
                            <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${visit.color}"></span>
                            <span>AQI ${visit.aqi} • ${visit.category} (${visit.time})</span>
                        </span>
                    `;
                }

                if (aqiSlot) {
                    const existingBtn = aqiSlot.querySelector('.card-fav-star');
                    const btnHtml = existingBtn ? existingBtn.outerHTML : '';
                    aqiSlot.innerHTML = `
                        <span class="text-xl font-black tracking-tight" style="color: ${visit.color}">${visit.aqi}</span>
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

    // Initialize all components on DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        initCitySearch();
        renderFavoritesBar();
        initFavoriteButton();
        renderForecastChart();
        renderTrendsChart();
        saveCurrentCityVisit();
        hydrateCatalogCardsFromLocalStorage();
        initCardFavoriteButtons();

        // Re-render charts on window resize
        let resizeTimer = null;
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                renderForecastChart();
                renderTrendsChart();
            }, 200);
        });
    });

    // Also run immediately in case DOM is already ready
    if (document.readyState === 'interactive' || document.readyState === 'complete') {
        initCitySearch();
        renderFavoritesBar();
        initFavoriteButton();
        renderForecastChart();
        renderTrendsChart();
        saveCurrentCityVisit();
        hydrateCatalogCardsFromLocalStorage();
        initCardFavoriteButtons();
    }
})();
