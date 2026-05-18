/**
 * Lexora Service Worker — M36 PWA + Offline Sync (S5: caching)
 *
 * Served from a controller at /sw.js (root scope) — see
 * src/addons/language_learning/controllers/portal_pwa.py.
 *
 * S5 fills in the caching machinery so the mobile-practice subtree
 * opens cleanly in airplane mode. Three caching strategies are wired,
 * scoped STRICTLY (sub-decision 35f — never serve a stale Odoo page):
 *
 *   ┌────────────────────────────────────────────┬───────────────────────────┐
 *   │ URL pattern                                │ Strategy                  │
 *   ├────────────────────────────────────────────┼───────────────────────────┤
 *   │ URL in PRECACHE_URLS                       │ cache-first + SWR         │
 *   │ /my/practice/mobile (navigation)           │ network-first + cached    │
 *   │                                            │   fallback when offline   │
 *   │ /lexora_api/{offline_batch,sync_offline}   │ ALWAYS network (no cache) │
 *   │ Anything else                              │ Pass-through (no respond) │
 *   └────────────────────────────────────────────┴───────────────────────────┘
 *
 * Update policy (sub-decision 35d): subsequent updates DO NOT call
 * self.skipWaiting() — the mobile UI shows an in-page "Lexora was
 * updated — refresh" banner and the user controls when to reload via
 * the SKIP_WAITING postMessage chain at the bottom of this file.
 *
 * VERSION constant doubles as the cache name; bump it whenever the
 * precache list or SW behaviour changes. The 'activate' handler
 * deletes any cache whose name doesn't match the current VERSION so
 * old shells don't accumulate.
 */

'use strict';

// VERSION bumped to v2 for M37. The byte change in this file
// triggers the M36-S5 user-controlled-update flow on existing
// users' next visit — a real production exercise of the banner
// + Refresh chain. The activate handler prunes the old
// `lexora-pwa-v1` cache automatically.
const VERSION = 'lexora-pwa-v2';
const LOG_PREFIX = '[lexora-sw]';

// ── Precache list (the offline shell) ────────────────────────────────
//
// Seven stable URLs. Static-asset URLs land at predictable paths under
// /language_learning/static/src/... because Odoo's `static/` convention
// serves them WITHOUT the asset-bundler's hash prefix — they're not
// in `web.assets_frontend`, just on disk. The web manifest is served
// by our own controller at the root.
//
// NOT precached: /my/practice/mobile (HTML). It requires authentication
// + carries user-specific initial cards. Caching it at install would
// either fail (no session) or pollute every user's cache with each
// other's initial set. Instead, the mobile-navigation fetch handler
// below caches it opportunistically on each successful network load.
const PRECACHE_URLS = [
  '/lexora.webmanifest',
  '/language_learning/static/src/css/mobile_practice.css',
  '/language_learning/static/src/js/vendor/idb.umd.js',
  '/language_learning/static/src/js/lexora_db.js',
  '/language_learning/static/src/js/mobile_practice.js',
  '/language_learning/static/src/icons/icon-192.png',
  '/language_learning/static/src/icons/icon-512.png',
];

// ── Routing helpers ──────────────────────────────────────────────────
//
// Pre-build a Set from PRECACHE_URLS for O(1) membership checks in the
// fetch handler. Regex matchers for the two scoped path patterns.
const PRECACHE_SET = new Set(PRECACHE_URLS);
const MOBILE_PRACTICE_RE = /^\/my\/practice\/mobile(?:\/|$)/;
// M37 adds offline_vocabulary as the third always-network path. The
// dictionary's IDB cache owns offline data; cached JSON responses
// would surface stale word lists if they ever leaked back to the
// app (they wouldn't actually — Cache-Control: no-store is set on
// the route — but explicit listing is documentation + future-proofing).
const LEXORA_API_RE      = /^\/lexora_api\/(?:offline_batch|sync_offline|offline_vocabulary)(?:\?|$)/;

// ── install: open cache + addAll precache list ───────────────────────
self.addEventListener('install', (event) => {
  console.log(LOG_PREFIX, 'install', VERSION,
    '(precache list:', PRECACHE_URLS.length, 'URLs)');

  event.waitUntil(
    caches.open(VERSION).then((cache) => {
      // addAll is atomic — if ANY URL 404s, the whole install fails
      // and the SW stays in the redundant state. That's actually what
      // we want: a broken precache list = broken offline mode, better
      // to fail loud at install than silently serve missing assets.
      return cache.addAll(PRECACHE_URLS);
    }).then(() => {
      // First-ever install: no prior SW to displace, no user state at
      // risk — skipWaiting is safe and gives the user offline support
      // on their very first visit. Subsequent updates skip this branch
      // and stay in 'waiting' until the user clicks Refresh in the
      // banner (sub-decision 35d).
      if (!self.registration.active) {
        return self.skipWaiting();
      }
      return undefined;
    }).catch((err) => {
      console.error(LOG_PREFIX, 'install failed:', err);
      // Re-throw so the SW transitions to the 'redundant' state and the
      // browser will retry on the next page load.
      throw err;
    })
  );
});

// ── activate: prune stale caches ─────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log(LOG_PREFIX, 'activate', VERSION);

  event.waitUntil((async () => {
    // Delete any cache whose name doesn't match the current VERSION.
    // After an update with a bumped VERSION constant, the old
    // 'lexora-pwa-vN' cache becomes orphaned — purge it to recover
    // storage. Single async loop; we don't `await` inside the filter
    // because Promise.all parallelises the deletes.
    const keys = await caches.keys();
    await Promise.all(
      keys.filter((k) => k !== VERSION).map((k) => {
        console.log(LOG_PREFIX, 'pruning stale cache:', k);
        return caches.delete(k);
      })
    );

    // We intentionally do NOT call self.clients.claim() here. The
    // user-controlled update rule (sub-decision 35d) means we let the
    // old SW keep serving open tabs until the user explicitly reloads
    // via the banner Refresh button. clients.claim() would yank
    // control away from a mid-review session.
  })());
});

// ── fetch: strict scoped routing ─────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const request = event.request;

  // We only own GETs. PUT/POST/DELETE etc. always go straight to the
  // network — caching mutating requests is never right.
  if (request.method !== 'GET') return;

  let url;
  try { url = new URL(request.url); }
  catch (_) { return; }   // Malformed URL — pass through to browser

  // Cross-origin requests are out of scope. Let the browser handle
  // youtube.com, fonts.googleapis.com, etc. without our involvement.
  if (url.origin !== self.location.origin) return;

  // ── Strategy 1: always-network for the live sync API ─────────────
  // The IndexedDB layer owns offline data; the API is for fresh
  // server-side state ONLY. Returning a cached batch would surface
  // stale due-dates and corrupt SM-2 scheduling.
  if (LEXORA_API_RE.test(url.pathname)) return;   // passthrough

  // ── Strategy 2: precached shell — cache-first + revalidate ───────
  if (PRECACHE_SET.has(url.pathname)) {
    event.respondWith(_cacheFirstSWR(request));
    return;
  }

  // ── Strategy 3: mobile-practice navigation — network-first w/ fallback
  // Match both the explicit navigation case (request.mode === 'navigate')
  // and a direct GET that happens to land on the same path (e.g. a
  // service-worker pre-cache attempt or a developer's curl). Both should
  // land here so the offline-fallback flow works regardless of entry.
  if (MOBILE_PRACTICE_RE.test(url.pathname)) {
    event.respondWith(_networkFirstNav(request));
    return;
  }

  // ── Default: pass-through ────────────────────────────────────────
  // We deliberately don't call event.respondWith here. The implicit
  // fall-through equals the browser's native fetch behaviour — no
  // caching, no interference. Sub-decision 35f: the SW MUST NEVER
  // serve a stale Odoo page outside its declared scope.
});

// ── Strategy implementations ────────────────────────────────────────

/**
 * Cache-first with stale-while-revalidate.
 *
 *   1. Look up the request in the cache.
 *   2. If hit: return it IMMEDIATELY (fast path — zero network round-trip).
 *   3. In parallel, fire a background fetch. On success, update the
 *      cache with the fresh response. The current page already has
 *      the cached version, so the update materialises on the NEXT
 *      page load.
 *   4. If cache MISS: await the network and return that response,
 *      writing it to the cache for next time.
 *   5. If both miss + network fails: return a 504 placeholder so the
 *      browser at least sees an HTTP response (better than a hanging
 *      fetch).
 */
async function _cacheFirstSWR(request) {
  const cache = await caches.open(VERSION);
  const cached = await cache.match(request);

  // Fire the background revalidate regardless of whether we have a
  // cache hit. Defensive .catch so a network failure doesn't reject
  // the surrounding promise — we already have (or will return) the
  // cached version.
  const networkPromise = fetch(request).then((resp) => {
    if (resp && resp.ok) {
      // .put() consumes the response stream, so clone before handing
      // the original back to the caller.
      cache.put(request, resp.clone()).catch(() => {});
    }
    return resp;
  }).catch(() => null);

  if (cached) return cached;

  const fresh = await networkPromise;
  if (fresh) return fresh;
  return new Response('Offline and not in precache', { status: 504 });
}

/**
 * Network-first with cache fallback.
 *
 * Used for the mobile-practice HTML navigation. The strategy:
 *
 *   1. Always try the network first. The HTML carries user-specific
 *      `<script id="lx-initial-cards">` JSON; we want it fresh whenever
 *      the user is online.
 *   2. On success, write the response to the cache (best-effort —
 *      .put failures don't fail the request).
 *   3. On network failure: serve the LAST cached version.
 *   4. If neither network nor cache works: return a 504. The user is
 *      offline AND has never visited the page before, which is a
 *      legitimately broken state — there's nothing we can do.
 */
async function _networkFirstNav(request) {
  const cache = await caches.open(VERSION);
  try {
    const resp = await fetch(request);
    if (resp && resp.ok) {
      cache.put(request, resp.clone()).catch(() => {});
    }
    return resp;
  } catch (_) {
    const cached = await cache.match(request);
    if (cached) return cached;
    return new Response(
      'Offline. Open this page online once before going airplane-mode.',
      { status: 504, headers: { 'Content-Type': 'text/plain; charset=utf-8' } }
    );
  }
}

// ── message: SKIP_WAITING from the mobile UI's update banner ────────
//
// The mobile-practice page's update banner sends this when the user
// clicks Refresh. We respond by calling self.skipWaiting(), which
// transitions the waiting SW to active. The page's controllerchange
// listener then reloads, serving the new shell.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log(LOG_PREFIX, 'loaded', VERSION);
