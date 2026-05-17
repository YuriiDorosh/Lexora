/**
 * Lexora Service Worker — M36 PWA + Offline Sync
 *
 * Served from a controller at /sw.js (root scope) — see
 * src/addons/language_learning/controllers/portal_pwa.py.
 *
 * S1 ships the skeleton: install / activate / fetch listeners that
 * pass through to the network. Caching + scoped routing lands in S5.
 *
 * Update policy (sub-decision 35d): we do NOT call self.skipWaiting()
 * on update — that would swap a freshly-installed SW in over a user
 * who's mid-review with a non-empty IndexedDB sync_queue. Instead the
 * mobile UI shows an in-page "Lexora was updated — refresh" banner
 * and the user controls when to reload.
 *
 * The first-ever install can call skipWaiting freely because there is
 * no prior SW to displace and no existing user state to disturb.
 *
 * VERSION constant doubles as the cache name in S5; bump it whenever
 * the precache list or the SW behaviour changes.
 */

'use strict';

const VERSION = 'lexora-pwa-v1';
const LOG_PREFIX = '[lexora-sw]';

self.addEventListener('install', (event) => {
  console.log(LOG_PREFIX, 'install', VERSION);
  // S1 — no precache yet. S5 will:
  //   event.waitUntil(
  //     caches.open(VERSION).then((cache) => cache.addAll(PRECACHE_URLS))
  //   );
  //
  // First-install skipWaiting is safe (no prior SW to displace).
  // Subsequent updates DO NOT call skipWaiting — the mobile UI shows
  // the user a refresh banner and they choose when to activate.
  if (!self.registration.active) {
    self.skipWaiting();
  }
});

self.addEventListener('activate', (event) => {
  console.log(LOG_PREFIX, 'activate', VERSION);
  // S5 will delete stale caches whose name != VERSION here.
  // For S1, just claim no clients — the user-controlled-update rule
  // means we want the new SW to wait for an explicit page reload
  // before taking over from the old one.
  //
  // We do NOT call self.clients.claim() — same rationale as above.
});

self.addEventListener('fetch', (event) => {
  // S1 — every request passes through to the network. S5 will add
  // strict scoping:
  //   - URL in PRECACHE_URLS                              → cache-first
  //   - /my/practice/mobile(/|$)                          → network-first w/ cache fallback
  //   - /lexora_api/(offline_batch|sync_offline)          → always network
  //   - anything else                                     → passthrough
  //
  // For S1 we deliberately leave this as the implicit passthrough so
  // the SW can be registered and inspected without altering any
  // existing Odoo behaviour. NO event.respondWith() = browser's
  // default network fetch.
});

// Listener for in-page messages from mobile_practice.js — S5 will
// add a SKIP_WAITING handler so the user's Refresh-button click can
// force the new SW to activate on the next page load.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log(LOG_PREFIX, 'loaded', VERSION);
