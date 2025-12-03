// Service worker for Hubx PWA

// Atualize o sufixo (v2, v3...) quando mudar assets importantes
const CACHE_NAME = "hubx-static-v2";

// Assets principais para funcionar offline (shell do app)
const CORE_ASSETS = [
  "/", // página inicial / shell principal
  // Se tiver uma página offline dedicada, descomente:
  // "/offline/",
  // Ícones PWA (ajuste o caminho se o STATIC_URL for diferente)
  "/static/icons/icon-96x96.png",
  "/static/icons/icon-128x128.png",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-256x256.png",
  "/static/icons/icon-384x384.png",
  "/static/icons/icon-512x512.png",
  "/static/icons/favicon-32x32.png",
  "/static/icons/favicon-16x16.png",
  "/static/icons/apple-touch-icon.png"
];

// Instalação: pré-cache dos assets principais
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(CORE_ASSETS))
  );
  self.skipWaiting();
});

// Ativação: limpa caches antigos
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Estratégia stale-while-revalidate para estáticos e rotas core
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request)
    .then(response => {
      if (response && response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);

  return cached || fetchPromise;
}

self.addEventListener("fetch", event => {
  // Só GET, não mexe com POST/PUT/etc.
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);

  const isStatic = /\.(css|js|png|svg|jpg|jpeg|gif|webp|woff2?|ico)$/.test(
    url.pathname
  );
  const isCoreRoute = CORE_ASSETS.includes(url.pathname);

  if (isStatic || isCoreRoute) {
    event.respondWith(staleWhileRevalidate(event.request));
    return;
  }

  // Se quiser um fallback offline para navegação, pode fazer algo assim:
  // if (event.request.mode === "navigate") {
  //   event.respondWith(
  //     fetch(event.request).catch(() => caches.match("/offline/"))
  //   );
  // }
});
