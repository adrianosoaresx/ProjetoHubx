// Service worker for Hubx PWA
// Cache version. Update the suffix (e.g., -v2) to force cache refresh on deploys.
const CACHE_NAME = "hubx-static-v1";

// List of core resources to pre-cache for offline usage.
const CORE_ASSETS = ["/"];

self.addEventListener("install", event => {
  // Pre-cache core assets so the primary shell is available offline.
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(CORE_ASSETS))
  );
});

self.addEventListener("activate", event => {
  // Clean up old caches when a new version is activated.
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))
    )
  );
  // Take control of clients immediately so no reload is required.
  self.clients.claim();
});

// Helper implementing stale-while-revalidate strategy.
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request)
    .then(response => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);
  return cached || fetchPromise;
}

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  const isStatic = /\.(css|js|png|svg|jpg|jpeg|gif|woff2?)$/.test(url.pathname);
  const isCoreRoute = CORE_ASSETS.includes(url.pathname);
  if (!(isStatic || isCoreRoute)) return;
  event.respondWith(staleWhileRevalidate(event.request));
});
