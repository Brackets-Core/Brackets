// Service Worker de Brackets Web Hub
// Cachea la carcasa (App Shell) para apertura instantánea en 0 ms.
const CACHE_NAME = 'brackets-shell-v16';
const SHELL_ASSETS = [
  './',
  './index.html',
  './style.css',
  './github_adapter.js',
  './app.js',
  './manifest.webmanifest',
  './icon-192.svg',
  './icon-512.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Las llamadas a la API local o a GitHub REST API siempre van a la red en vivo
  if (
    req.method !== 'GET' ||
    url.pathname.startsWith('/api/') ||
    url.hostname === 'api.github.com'
  ) {
    return;
  }

  // Estrategia Network First con fallback a Cache para estáticos
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
        }
        return res;
      })
      .catch(() => caches.match(req).then((cached) => cached || caches.match('./index.html')))
  );
});
