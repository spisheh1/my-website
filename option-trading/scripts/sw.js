// Options Trader — Service Worker
// Strategy: cache the dashboard shell; always go to network for API calls.

const CACHE  = 'options-v1';
const SHELL  = ['/trading/'];  // pages to pre-cache on install

// ── Install: pre-cache the dashboard shell ───────────────────────────────────
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: clean up old caches ────────────────────────────────────────────
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: network-first for API/SSE, cache-first for shell ──────────────────
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Always use network for API endpoints and SSE stream
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request).catch(() =>
      new Response(JSON.stringify({ error: 'offline' }), {
        headers: { 'Content-Type': 'application/json' }
      })
    ));
    return;
  }

  // For the dashboard shell: try network first, fall back to cache
  e.respondWith(
    fetch(e.request)
      .then(res => {
        // Update cache with fresh response
        if (res.ok && e.request.method === 'GET') {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
