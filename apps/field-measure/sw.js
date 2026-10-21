// Service worker: precache the whole app, then serve cache-first with network fallback.
// Paths are relative to this file so the app works under any sub-path (e.g. GitHub Pages /-/apps/field-measure/).
// Bump CACHE when any listed file changes, otherwise phones keep the old copy.

const CACHE = 'fm-v2';
const PRECACHE = [
  './',
  './index.html',
  './style.css',
  './manifest.json',
  './icon.svg',
  './src/app.js',
  './src/store.js',
  './src/level.js',
  './src/road.js',
  './src/toilet.js',
  './src/dxf.js',
  './src/export.js',
  './src/views/home.js',
  './src/views/roadSettings.js',
  './src/views/station.js',
  './src/views/levelBook.js',
  './src/views/toilet.js',
  './src/views/exportPanel.js',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('fm-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  event.respondWith(
    caches.match(req, { ignoreSearch: true }).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok && res.type === 'basic') {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => (req.mode === 'navigate' ? caches.match('./index.html') : Response.error()))),
  );
});
