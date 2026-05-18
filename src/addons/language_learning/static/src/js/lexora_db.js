/**
 * lexora_db.js — IndexedDB data layer for M36 Mobile PWA & Offline Sync.
 *
 * Exposes `window.lexora.db` with the seven-method API locked in
 * ADR-035 § sub-decision 35c.
 *
 * Loaded AFTER `vendor/idb.umd.js`, which puts `window.idb.openDB` /
 * `window.idb.deleteDB` in scope. Browser-only — Node tests pull these
 * via the same global by polyfilling with `fake-indexeddb` + a manual
 * `globalThis.idb` shim.
 *
 * Database schema v1
 * ------------------
 *   db: lexora_offline
 *   ├── cards_to_review  (keyPath: 'id')
 *   │     One row per Odoo language.review card. Replaced wholesale
 *   │     by replaceCardsToReview() on every successful prefetch.
 *   │
 *   └── sync_queue       (keyPath: 'client_uuid')
 *         One row per offline review the user has graded. Keyed by a
 *         client-generated UUID so the upload is idempotent — the
 *         server's language.review.offline.log table dedupes via a
 *         UNIQUE(user_id, client_uuid) constraint (sub-decision 35c).
 *
 * Error envelope
 * --------------
 *   Write methods return either { ok: true, ...payload } on success or
 *   { ok: false, error: <kind>, message?: <details> } on failure, where
 *   <kind> is one of:
 *       'quota'        — QuotaExceededError; storage budget hit
 *       'aborted'      — transaction aborted (closed tab, etc.)
 *       'security'     — SecurityError; private-mode IDB blocked
 *       'unknown'      — anything else
 *
 *   Read methods return either { ok: true, ...payload } or
 *   { ok: false, error: <kind> }. Callers must not assume ok=true; the
 *   mobile UI surfaces a toast when error='quota' (storage full) and
 *   logs a console warning for the rest.
 *
 * The seven methods
 * -----------------
 *   await lexora.db.init()
 *   await lexora.db.replaceCardsToReview(cards)
 *   await lexora.db.enqueueReview({card_id, grade, reviewed_at_iso})
 *   await lexora.db.drainQueue()
 *   await lexora.db.removeFromQueue(uuidArray)
 *   await lexora.db.getDueCards({ asOf?, limit? })
 *   await lexora.db.stats()
 */

(function () {
  'use strict';

  // Locate the idb global. Browser: window.idb (from vendor UMD).
  // Node sandbox: globalThis.idb (the test harness sets this up via
  // `global.idb = require('idb')` after loading fake-indexeddb).
  const _IDB =
    (typeof globalThis !== 'undefined' && globalThis.idb) ||
    (typeof window !== 'undefined' && window.idb) ||
    null;

  if (!_IDB || typeof _IDB.openDB !== 'function') {
    // Defensive: a runtime missing idb is a hard programming error —
    // the vendor UMD must be loaded BEFORE this script. We don't throw
    // here so the mobile-practice page can degrade gracefully and the
    // top-level catch in mobile_practice.js can surface a useful error
    // banner.
    console.error('[lexora.db] idb library not found — load vendor/idb.umd.js first');
  }

  // ── Configuration constants ────────────────────────────────────────
  const DB_NAME = 'lexora_offline';
  const DB_VERSION = 1;
  const STORE_CARDS = 'cards_to_review';
  const STORE_QUEUE = 'sync_queue';

  // Single persistent handle. _dbPromise is set by init() and re-used
  // by every subsequent call so we open the database exactly once per
  // page lifetime.
  let _dbPromise = null;

  // ── Error classification helper ────────────────────────────────────
  // IndexedDB exceptions surface as DOMException instances with .name
  // set to one of a known catalogue. We translate to short stable kinds
  // so the UI's toast logic can branch cleanly.
  function _classifyError(err) {
    if (!err) return { kind: 'unknown', message: 'no error object' };
    const name = err.name || '';
    let kind;
    if (name === 'QuotaExceededError') kind = 'quota';
    else if (name === 'AbortError')    kind = 'aborted';
    else if (name === 'SecurityError') kind = 'security';
    else                                kind = 'unknown';
    return { kind, message: err.message || String(err) };
  }

  // ── init() — open + upgrade the database ───────────────────────────
  // Idempotent: returns the cached promise on subsequent calls. The
  // upgrade callback runs only when the stored version is lower than
  // DB_VERSION; for a fresh database both stores are created.
  async function init() {
    if (_dbPromise) {
      try { await _dbPromise; return { ok: true, reused: true }; }
      catch (err) {
        _dbPromise = null;
        const { kind, message } = _classifyError(err);
        return { ok: false, error: kind, message };
      }
    }
    if (!_IDB) {
      return { ok: false, error: 'unknown', message: 'idb library not loaded' };
    }

    _dbPromise = _IDB.openDB(DB_NAME, DB_VERSION, {
      upgrade(db, oldVersion /*, newVersion, transaction, event */) {
        // v0 → v1: create both stores. Schema migrations for future
        // versions land as additional `if (oldVersion < N)` blocks.
        if (oldVersion < 1) {
          if (!db.objectStoreNames.contains(STORE_CARDS)) {
            db.createObjectStore(STORE_CARDS, { keyPath: 'id' });
          }
          if (!db.objectStoreNames.contains(STORE_QUEUE)) {
            db.createObjectStore(STORE_QUEUE, { keyPath: 'client_uuid' });
          }
        }
      },
      blocked() {
        // Another tab holds a connection at an older version. The
        // browser will eventually deliver `versionchange` events to
        // those tabs; we just log here so a stuck open is visible.
        console.warn('[lexora.db] open blocked by another tab');
      },
      terminated() {
        // The connection died (private-mode storage flush, OS-level
        // eviction, etc.). Drop the cached promise so the next call
        // re-opens cleanly.
        console.warn('[lexora.db] connection terminated; will reopen on next call');
        _dbPromise = null;
      },
    });

    try {
      await _dbPromise;
      return { ok: true, reused: false };
    } catch (err) {
      _dbPromise = null;
      const { kind, message } = _classifyError(err);
      return { ok: false, error: kind, message };
    }
  }

  async function _getDb() {
    if (!_dbPromise) {
      // Self-heal: callers should call init() first but the UI can
      // accidentally race a method against a pending init(). Open
      // lazily; the cached promise pattern de-duplicates concurrent
      // callers automatically.
      const result = await init();
      if (!result.ok) throw new Error('db init failed: ' + result.error);
    }
    return _dbPromise;
  }

  // ── replaceCardsToReview(cards) ────────────────────────────────────
  // Wholesale replace of the cards_to_review store. Used by the
  // mobile-practice page after a successful GET /lexora_api/offline_batch.
  // Single transaction so the store either has the new set or the old
  // — never a half-written mix.
  async function replaceCardsToReview(cards) {
    if (!Array.isArray(cards)) {
      return { ok: false, error: 'unknown', message: 'cards must be an array' };
    }
    try {
      const db = await _getDb();
      const tx = db.transaction(STORE_CARDS, 'readwrite');
      await tx.store.clear();
      for (const card of cards) {
        if (card && typeof card.id !== 'undefined') {
          await tx.store.put(card);
        }
      }
      await tx.done;
      return { ok: true, count: cards.length };
    } catch (err) {
      const { kind, message } = _classifyError(err);
      console.warn('[lexora.db] replaceCardsToReview failed:', kind, message);
      return { ok: false, error: kind, message };
    }
  }

  // ── enqueueReview({ card_id, grade, reviewed_at_iso }) ─────────────
  // Stamps a fresh client_uuid + enqueued_at_iso and puts the row into
  // the sync_queue store. This is the ONLY method that can be called
  // while offline — every other write needs network or just doesn't
  // make sense without it.
  async function enqueueReview(review) {
    if (!review || typeof review.card_id === 'undefined') {
      return { ok: false, error: 'unknown', message: 'card_id required' };
    }
    const grade = Number(review.grade);
    if (!Number.isFinite(grade)) {
      return { ok: false, error: 'unknown', message: 'grade must be a number' };
    }
    try {
      // crypto.randomUUID() is available in modern browsers (Chrome 92+,
      // Safari 15.4+, all our target platforms). Defensive fallback for
      // the Node sandbox: webcrypto exposes it at globalThis.crypto.
      let client_uuid;
      if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        client_uuid = crypto.randomUUID();
      } else {
        // RFC 4122 v4 fallback — only reached in environments without
        // webcrypto, which shouldn't happen in our supported targets.
        client_uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
          const r = (Math.random() * 16) | 0;
          const v = c === 'x' ? r : (r & 0x3) | 0x8;
          return v.toString(16);
        });
      }

      const row = {
        client_uuid,
        card_id: review.card_id,
        grade,
        reviewed_at_iso: review.reviewed_at_iso || new Date().toISOString(),
        enqueued_at_iso: new Date().toISOString(),
      };

      const db = await _getDb();
      const tx = db.transaction(STORE_QUEUE, 'readwrite');
      await tx.store.put(row);
      await tx.done;
      return { ok: true, client_uuid, row };
    } catch (err) {
      const { kind, message } = _classifyError(err);
      console.warn('[lexora.db] enqueueReview failed:', kind, message);
      return { ok: false, error: kind, message };
    }
  }

  // ── drainQueue() ───────────────────────────────────────────────────
  // Pulls all queued reviews for upload. CRITICALLY does not delete —
  // deletion only happens via removeFromQueue() after the server
  // confirms each UUID processed. This guarantees that a mid-flight
  // network drop preserves the queue (sub-decision 35c).
  async function drainQueue() {
    try {
      const db = await _getDb();
      const all = await db.getAll(STORE_QUEUE);
      return { ok: true, queue: all };
    } catch (err) {
      const { kind, message } = _classifyError(err);
      console.warn('[lexora.db] drainQueue failed:', kind, message);
      return { ok: false, error: kind, message };
    }
  }

  // ── removeFromQueue(uuidArray) ─────────────────────────────────────
  // Delete the UUIDs the server has confirmed processed. Bulk-delete
  // in a single transaction so partial failures don't leave the queue
  // in a torn state.
  async function removeFromQueue(uuids) {
    if (!Array.isArray(uuids)) {
      return { ok: false, error: 'unknown', message: 'uuids must be an array' };
    }
    if (!uuids.length) return { ok: true, removed: 0 };
    try {
      const db = await _getDb();
      const tx = db.transaction(STORE_QUEUE, 'readwrite');
      for (const uuid of uuids) {
        if (typeof uuid === 'string' && uuid) {
          await tx.store.delete(uuid);
        }
      }
      await tx.done;
      return { ok: true, removed: uuids.length };
    } catch (err) {
      const { kind, message } = _classifyError(err);
      console.warn('[lexora.db] removeFromQueue failed:', kind, message);
      return { ok: false, error: kind, message };
    }
  }

  // ── getDueCards({ asOf?, limit? }) ─────────────────────────────────
  // Read-only filter over the cards_to_review store. Sort order matches
  // language.review.get_due_cards on the server side (state desc,
  // next_review_date_iso asc) so the offline session feels identical
  // to the desktop one.
  async function getDueCards({ asOf, limit } = {}) {
    try {
      const cutoff = asOf instanceof Date ? asOf : new Date(asOf || Date.now());
      const cutoffIso = cutoff.toISOString();
      const db = await _getDb();
      const all = await db.getAll(STORE_CARDS);
      // Filter: card's next_review_date_iso <= cutoff (or unset = treat as due).
      const due = all.filter((c) => {
        if (!c.next_review_date_iso) return true;
        return c.next_review_date_iso <= cutoffIso;
      });
      // Sort: state desc (learning/review come before new — same order
      // as language.review.get_due_cards). Then next_review_date_iso asc.
      const stateRank = { learning: 0, new: 1, review: 2 };
      due.sort((a, b) => {
        const ra = stateRank[a.srs_state] ?? 99;
        const rb = stateRank[b.srs_state] ?? 99;
        if (ra !== rb) return ra - rb;
        const da = a.next_review_date_iso || '';
        const db2 = b.next_review_date_iso || '';
        return da < db2 ? -1 : da > db2 ? 1 : 0;
      });
      const sliced = typeof limit === 'number' && limit > 0 ? due.slice(0, limit) : due;
      return { ok: true, cards: sliced, total: due.length };
    } catch (err) {
      const { kind, message } = _classifyError(err);
      console.warn('[lexora.db] getDueCards failed:', kind, message);
      return { ok: false, error: kind, message };
    }
  }

  // ── stats() ────────────────────────────────────────────────────────
  // Diagnostic counter — the mobile UI uses cardCount for the
  // "X / Y cards" header and queuedCount for the sync-button badge.
  async function stats() {
    try {
      const db = await _getDb();
      const cardCount = await db.count(STORE_CARDS);
      const queuedCount = await db.count(STORE_QUEUE);
      return {
        ok: true,
        cardCount,
        queuedCount,
        dbVersion: DB_VERSION,
        dbName: DB_NAME,
      };
    } catch (err) {
      const { kind, message } = _classifyError(err);
      console.warn('[lexora.db] stats failed:', kind, message);
      return { ok: false, error: kind, message };
    }
  }

  // ── Public API export ──────────────────────────────────────────────
  const api = {
    init,
    replaceCardsToReview,
    enqueueReview,
    drainQueue,
    removeFromQueue,
    getDueCards,
    stats,
    // Internal constants exposed for the Node sandbox test only.
    _internals: { DB_NAME, DB_VERSION, STORE_CARDS, STORE_QUEUE },
  };

  if (typeof window !== 'undefined') {
    window.lexora = window.lexora || {};
    window.lexora.db = api;
  }
  // Also expose on globalThis for the Node sandbox.
  if (typeof globalThis !== 'undefined') {
    globalThis.lexora = globalThis.lexora || {};
    globalThis.lexora.db = api;
  }
  // CommonJS export so the Node test can `require()` directly.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})();
