const CACHE_NAME = "college-site-v3";
const ASSETS = ["/static/style.css", "/static/script.js", "/static/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = event.request.url;

  if (url.includes("/api/chat") || url.includes("/admin") || url.includes("/login")) {
    return;
  }

  // Pages (HTML / navigation): always try the network first so updates
  // (like a new Login button) show up immediately. Fall back to cache
  // only if there's no internet connection. If neither works, return a
  // plain offline response instead of `undefined` (which the browser
  // cannot turn into a Response and throws an error for).
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match(event.request).then(
          (cached) => cached || new Response("You're offline. Please check your internet connection.", {
            status: 503,
            headers: { "Content-Type": "text/plain" },
          })
        )
      )
    );
    return;
  }

  // Static assets (CSS/JS/images): cache-first for speed, but refresh
  // the cache in the background so the next visit gets the latest file.
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request)
        .then((response) => {
          // IMPORTANT: clone the response immediately/synchronously, before
          // it is returned and its body starts being read elsewhere.
          // Cloning it later (e.g. inside a nested .then) can fail with
          // "Response body is already used" once the original body has
          // already started being consumed.
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
          return response;
        })
        .catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
