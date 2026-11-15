/**
 * AirTrace v3.3 Service Worker
 * Progressive Web App caching, offline resilience, and background sync support.
 */

const CACHE_NAME = 'airtrace-v3.3-cache-v1';

const PRECACHE_ASSETS = [
    '/',
    '/static/style.css',
    '/static/js/airtrace_v3.js',
    '/static/favicon.svg',
    '/static/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(PRECACHE_ASSETS);
        }).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const request = event.request;

    // Only handle GET requests
    if (request.method !== 'GET') return;

    const url = new URL(request.url);

    // Bypass API calls to let them fail transparently or handle via client-side cache
    if (url.pathname.startsWith('/v1/') || url.pathname.startsWith('/v2/') || url.pathname.startsWith('/v3/')) {
        return;
    }

    // HTML Navigation requests: Network-first, fallback to cache
    if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    if (response && response.status === 200) {
                        const copy = response.clone();
                        event.waitUntil(
                            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy)).catch(() => {})
                        );
                    }
                    return response;
                })
                .catch(async () => {
                    const cached = await caches.match(request);
                    if (cached) return cached;
                    const indexCached = await caches.match('/');
                    if (indexCached) return indexCached;
                    return new Response(
                        `<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>Оффлайн — AirTrace</title><style>body{background:#0b1220;color:#fff;font-family:sans-serif;text-align:center;padding:40px;}</style></head><body><h1>Вы находитесь в оффлайн-режиме</h1><p>Проверьте подключение к интернету для получения свежих замеров.</p><a href="/" style="color:#2dd4bf">Попробовать снова</a></body></html>`,
                        { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
                    );
                })
        );
        return;
    }

    // Static assets: Stale-while-revalidate
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then((cached) => {
                const networkFetch = fetch(request).then((response) => {
                    if (response && response.status === 200) {
                        const copy = response.clone();
                        event.waitUntil(
                            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy)).catch(() => {})
                        );
                    }
                    return response;
                }).catch(() => cached);

                return cached || networkFetch;
            })
        );
    }
});
