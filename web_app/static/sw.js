const CACHE_NAME = 'epub-editor-v3';
const STATIC_ASSETS = [
  '/static/style.css?v=3',
  '/static/manifest.json?v=3',
  '/static/icon-192.png?v=3',
  '/static/icon-512.png?v=3',
];

// Install: cache static assets (skip HTML to always fetch fresh)
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: network-first for HTML/API, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  // API calls: network only
  if (url.pathname.startsWith('/upload') ||
      url.pathname.startsWith('/save') ||
      url.pathname.startsWith('/cover') ||
      url.pathname.startsWith('/update-cover') ||
      url.pathname.startsWith('/remove-cover') ||
      url.pathname.startsWith('/cover-from-url') ||
      url.pathname.startsWith('/clean')) {
    return;
  }

  // HTML page: always fetch fresh (never cache)
  if (url.pathname === '/' || url.pathname === '/index.html') {
    event.respondWith(fetch(request));
    return;
  }

  // Static assets: cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request).then((response) => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      }).catch(() => cached);
    })
  );
});
