/**
 * mobile_practice.js — M36 Mobile Practice page controller.
 *
 * Exposes `window.lexora.mobile.boot()` (called automatically on
 * DOMContentLoaded at the bottom of this file). Drives the full UI
 * state machine:
 *
 *   1. Register the Service Worker at /sw.js (no-op if not supported).
 *   2. Initialise IndexedDB via lexora.db.init().
 *   3. On first run (empty IDB), hydrate from the
 *      <script id="lx-initial-cards"> JSON the server injected.
 *   4. Background-prefetch a fresh batch via /lexora_api/offline_batch
 *      when online — keeps the deck fresh across sessions.
 *   5. Render the first due card. Tap flips. Tap on Forgot or
 *      Remembered grades. Swipe left = Forgot, right = Remembered.
 *   6. Each grade calls lexora.db.enqueueReview() (queues to
 *      sync_queue regardless of network), then advances the card.
 *      If online, immediately attempts to flush the queue.
 *   7. window 'online' / 'offline' events update the connection
 *      indicator + trigger a sync attempt on reconnect.
 *   8. The SW update banner is wired via navigator.serviceWorker's
 *      registration.installing / waiting / controllerchange lifecycle
 *      per ADR-035 § 35d.
 *
 * No build step; vanilla ES2020. The vendored idb UMD + lexora_db.js
 * must load BEFORE this script (the QWeb template orders the <script>
 * tags accordingly).
 */

(function () {
  'use strict';

  // ── Namespace ──────────────────────────────────────────────────
  const NS = (window.lexora = window.lexora || {});
  NS.mobile = NS.mobile || {};

  // ── DOM handles (resolved at boot) ─────────────────────────────
  let $root, $progressCur, $progressTotal, $syncBtn, $queueBadge, $conn,
      $stage, $loading, $empty, $card, $cardWord, $cardState, $cardTrans,
      $actionsRow, $forgotBtn, $rememberedBtn, $toast,
      $updateBanner, $updateRefresh;

  // ── Runtime state ──────────────────────────────────────────────
  // _cards is the in-memory snapshot of the current deck. We pull it
  // from IDB on boot and replace it after a successful background
  // prefetch. _index is the cursor into that array. We never mutate
  // _cards mid-session except to slice off the head as the user
  // advances — keeps the "X / Y" progress count honest.
  const state = {
    cards: [],        // current deck snapshot
    index: 0,         // cursor into cards
    flipped: false,
    online: navigator.onLine,
    syncing: false,
    swRegistration: null,
    waitingWorker: null,
  };

  // Static flag map for the translation rows on the card back.
  const LANG_FLAGS = { en: '🇬🇧', uk: '🇺🇦', el: '🇬🇷', pl: '🇵🇱' };
  const LANG_ORDER = ['uk', 'el', 'pl', 'en'];

  // Swipe gesture thresholds. Px from start that classifies as a
  // commit (vs snap-back). Empirically: 60-70 px feels right on a
  // phone; under 60 produces false-positives when the user just taps.
  const SWIPE_COMMIT_PX = 70;
  // Above this time, we treat the touch as a long-press / hesitation,
  // not a swipe — snap back regardless of distance.
  const SWIPE_MAX_MS = 600;

  // ── DOM helpers ────────────────────────────────────────────────
  function _$(id) { return document.getElementById(id); }
  function _show(el) { if (el) el.classList.remove('d-none'); }
  function _hide(el) { if (el) el.classList.add('d-none'); }

  function _escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _toast(kind, message, durationMs) {
    if (!$toast) return;
    $toast.className = 'lx-mp-toast lx-mp-toast-' + (kind || 'ok');
    $toast.textContent = message;
    _show($toast);
    clearTimeout(_toast._t);
    _toast._t = setTimeout(() => _hide($toast), durationMs || 2200);
  }

  // ── Initial-cards hydration ────────────────────────────────────
  function _readInitialCards() {
    const tag = document.getElementById('lx-initial-cards');
    if (!tag) return [];
    try {
      const txt = (tag.textContent || '').trim();
      if (!txt) return [];
      const parsed = JSON.parse(txt);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      console.warn('[lexora.mobile] could not parse initial cards JSON:', e);
      return [];
    }
  }

  // ── Service Worker registration ────────────────────────────────
  async function _registerServiceWorker() {
    if (!('serviceWorker' in navigator)) {
      console.warn('[lexora.mobile] Service Worker API unavailable; offline disabled.');
      return null;
    }
    try {
      const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      console.log('[lexora.mobile] SW registered, scope:', reg.scope);
      state.swRegistration = reg;

      // Wire the update-detection chain. A new SW may already be
      // waiting (if the page reloaded while one was installed) — or
      // it may install during this session via reg.installing.
      const checkWaiting = () => {
        if (reg.waiting && navigator.serviceWorker.controller) {
          state.waitingWorker = reg.waiting;
          _show($updateBanner);
        }
      };
      checkWaiting();
      reg.addEventListener('updatefound', () => {
        const installing = reg.installing;
        if (!installing) return;
        installing.addEventListener('statechange', () => {
          if (installing.state === 'installed' && navigator.serviceWorker.controller) {
            state.waitingWorker = installing;
            _show($updateBanner);
          }
        });
      });

      // controllerchange fires when the new SW takes control after
      // skipWaiting + reload. We reload the page so the new shell is
      // served from cache cleanly.
      let _reloadingForSw = false;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (_reloadingForSw) return;
        _reloadingForSw = true;
        window.location.reload();
      });

      return reg;
    } catch (err) {
      console.warn('[lexora.mobile] SW registration failed:', err);
      return null;
    }
  }

  // ── Background prefetch ────────────────────────────────────────
  async function _prefetchBatch() {
    if (!state.online) return;
    try {
      const resp = await fetch('/lexora_api/offline_batch?days=7&limit=200', {
        method: 'GET',
        credentials: 'include',
        cache: 'no-store',
      });
      if (resp.status === 401) {
        _toast('warn', 'Session expired — please sign in to refresh your deck');
        return;
      }
      if (!resp.ok) {
        console.warn('[lexora.mobile] /offline_batch HTTP', resp.status);
        return;
      }
      const data = await resp.json();
      if (data && data.status === 'ok' && Array.isArray(data.cards)) {
        const result = await NS.db.replaceCardsToReview(data.cards);
        if (result.ok) {
          // Reload the in-memory deck from IDB. We don't disturb the
          // user's current card view — _cards is only touched once
          // they advance past the last in-memory card, which will
          // pick up the new set on the next render() call.
          //
          // For S4 simplicity: refresh the deck only if the user
          // hasn't started reviewing yet (index === 0 AND no flip).
          if (state.index === 0 && !state.flipped) {
            state.cards = data.cards;
            _renderCurrent();
          }
        }
      }
    } catch (e) {
      console.warn('[lexora.mobile] /offline_batch fetch failed:', e);
    }
  }

  // ── Render the active card ─────────────────────────────────────
  function _renderCurrent() {
    const total = state.cards.length;
    $progressCur.textContent = String(Math.min(state.index + (total ? 1 : 0), total));
    $progressTotal.textContent = String(total);

    if (state.index >= total) {
      // Deck exhausted (no due cards or finished session).
      _hide($card);
      _hide($actionsRow);
      _show($empty);
      return;
    }

    const card = state.cards[state.index];
    if (!card) {
      _hide($card);
      _hide($actionsRow);
      _show($empty);
      return;
    }

    // Reset flip + transform from any previous swipe animation.
    state.flipped = false;
    $card.classList.remove('lx-mp-flipped', 'lx-mp-swipe-left', 'lx-mp-swipe-right');
    $card.style.transform = '';
    $card.style.opacity = '';

    // Front face — word + SRS state badge.
    $cardWord.textContent = card.word || '';
    $cardState.textContent = card.srs_state || 'new';
    $cardState.className = 'lx-mp-card-state';
    if (card.srs_state) {
      $cardState.classList.add('lx-mp-state-' + card.srs_state);
    }

    // Back face — translations (rendered eagerly; the flip animation
    // hides them via backface-visibility until the user taps).
    const translations = card.translations || {};
    const order = LANG_ORDER.filter((l) => l !== card.lang && translations[l]);
    if (order.length) {
      $cardTrans.innerHTML = order.map((lang) => (
        '<div class="lx-mp-trans-row">' +
          '<span class="lx-mp-trans-flag">' + _escHtml(LANG_FLAGS[lang] || lang) + '</span>' +
          '<span class="lx-mp-trans-text">' + _escHtml(translations[lang]) + '</span>' +
        '</div>'
      )).join('');
    } else {
      $cardTrans.innerHTML =
        '<div class="lx-mp-trans-empty">No translations on file for this entry.</div>';
    }

    _hide($empty);
    _show($card);
    _show($actionsRow);
  }

  // ── Card flip + grade ──────────────────────────────────────────
  function _flipCard() {
    state.flipped = !state.flipped;
    $card.classList.toggle('lx-mp-flipped', state.flipped);
  }

  async function _grade(gradeInt, direction /* 'left'|'right'|null */) {
    const card = state.cards[state.index];
    if (!card) return;

    // Lock the buttons during the swipe-out animation so a double-tap
    // can't double-grade the same card.
    $forgotBtn.disabled = true;
    $rememberedBtn.disabled = true;

    // Visual swipe-out (CSS handles the translate + opacity transition).
    if (direction === 'left' || direction === 'right') {
      $card.classList.add('lx-mp-swipe-' + direction);
    }

    // Enqueue to IDB sync_queue (works offline). enqueueReview returns
    // the synthetic client_uuid + row; we don't need it here but it's
    // logged in lexora_db.js if anything goes wrong.
    const enq = await NS.db.enqueueReview({
      card_id: card.id,
      grade: gradeInt,
      reviewed_at_iso: new Date().toISOString(),
    });
    if (!enq.ok) {
      if (enq.error === 'quota') {
        _toast('error', 'Storage full — please clear some space');
      } else {
        _toast('error', 'Could not save your review (will retry)');
      }
      $forgotBtn.disabled = false;
      $rememberedBtn.disabled = false;
      return;
    }

    // Animate the swipe-out, then advance. 240 ms ≈ CSS transition
    // duration in mobile_practice.css's .lx-mp-swipe-* rules.
    setTimeout(() => {
      state.index += 1;
      $forgotBtn.disabled = false;
      $rememberedBtn.disabled = false;
      _renderCurrent();
      _refreshQueueBadge();
    }, 240);

    // Best-effort sync. Doesn't block the UI advance.
    if (state.online) _syncQueue();
  }

  // ── Sync queued reviews ────────────────────────────────────────
  async function _syncQueue() {
    if (state.syncing) return;
    if (!state.online) return;
    const drained = await NS.db.drainQueue();
    if (!drained.ok || !drained.queue.length) {
      _refreshQueueBadge();
      return;
    }
    state.syncing = true;
    try {
      const payload = {
        reviews: drained.queue.map((r) => ({
          client_uuid: r.client_uuid,
          card_id: r.card_id,
          grade: r.grade,
          reviewed_at_iso: r.reviewed_at_iso,
        })),
      };
      const resp = await fetch('/lexora_api/sync_offline', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        cache: 'no-store',
      });
      if (resp.status === 401) {
        _toast('warn', 'Session expired — sign in to push your reviews', 4000);
        return;
      }
      if (!resp.ok) {
        _toast('warn', 'Sync failed (HTTP ' + resp.status + ') — will retry');
        return;
      }
      const data = await resp.json();
      if (!data || data.status !== 'ok') {
        _toast('warn', 'Sync rejected — will retry');
        return;
      }
      // Remove every UUID the server accepted (processed) OR rejected
      // as a duplicate. not_found rows we ALSO remove from the queue:
      // the card no longer exists for this user, so retrying is futile.
      // errors stay in the queue for the next sync attempt.
      const acceptedUuids = [];
      const errorUuids = new Set(
        (data.errors || []).map((e) => e && e.client_uuid).filter(Boolean)
      );
      for (const r of drained.queue) {
        if (!errorUuids.has(r.client_uuid)) acceptedUuids.push(r.client_uuid);
      }
      if (acceptedUuids.length) {
        await NS.db.removeFromQueue(acceptedUuids);
      }
      _refreshQueueBadge();
      const total = (data.processed || 0) + (data.skipped_duplicate || 0);
      if (total > 0) {
        _toast('ok', 'Synced ' + total + ' review' + (total === 1 ? '' : 's'));
      }
    } catch (e) {
      console.warn('[lexora.mobile] sync_offline fetch failed:', e);
      _toast('warn', 'Sync failed — will retry on next reconnect');
    } finally {
      state.syncing = false;
    }
  }

  async function _refreshQueueBadge() {
    try {
      const s = await NS.db.stats();
      if (!s.ok) return;
      if (s.queuedCount > 0) {
        $queueBadge.textContent = String(s.queuedCount);
        _show($queueBadge);
      } else {
        _hide($queueBadge);
      }
    } catch (_) { /* badge is cosmetic; never let it break boot */ }
  }

  // ── Connection-state listeners ─────────────────────────────────
  function _setOnline(isOnline) {
    state.online = isOnline;
    if ($conn) {
      $conn.classList.toggle('lx-mp-conn-online', isOnline);
      $conn.classList.toggle('lx-mp-conn-offline', !isOnline);
      $conn.title = isOnline ? 'Online' : 'Offline';
      $conn.setAttribute('aria-label', isOnline ? 'Online' : 'Offline');
    }
    if (isOnline) {
      _toast('ok', 'Back online — syncing…', 1600);
      _syncQueue();
      _prefetchBatch();
    } else {
      _toast('warn', 'Offline — your reviews will sync when you reconnect', 2400);
    }
  }

  // ── Swipe gestures ─────────────────────────────────────────────
  // Single touchstart → touchmove → touchend chain. We track the
  // starting X / Y / time on touchstart, translate the card during
  // touchmove, and on touchend either commit (>= SWIPE_COMMIT_PX) or
  // snap back. The snap-back is a CSS transition triggered by clearing
  // the inline transform.
  function _bindSwipe() {
    let startX = 0, startY = 0, startMs = 0, dragging = false, moved = false;

    function onStart(e) {
      const touch = e.touches ? e.touches[0] : e;
      startX = touch.clientX;
      startY = touch.clientY;
      startMs = Date.now();
      dragging = true;
      moved = false;
      // Disable the CSS transition during the drag so the card tracks
      // the finger 1:1 with no easing lag.
      $card.style.transition = 'none';
    }

    function onMove(e) {
      if (!dragging) return;
      const touch = e.touches ? e.touches[0] : e;
      const dx = touch.clientX - startX;
      const dy = touch.clientY - startY;
      // If vertical movement dominates, this is a scroll attempt —
      // bail out without disturbing the card. (The body has overflow
      // hidden so this only matters for the gesture-mode flag.)
      if (Math.abs(dy) > Math.abs(dx) + 16) return;
      if (Math.abs(dx) > 4) moved = true;
      const rot = (dx / 20).toFixed(2);
      $card.style.transform = 'translateX(' + dx + 'px) rotate(' + rot + 'deg)';
    }

    function onEnd(e) {
      if (!dragging) return;
      dragging = false;
      $card.style.transition = '';   // restore CSS transition
      const touch = (e.changedTouches && e.changedTouches[0]) || e;
      const dx = touch.clientX - startX;
      const elapsed = Date.now() - startMs;
      const fast = elapsed < SWIPE_MAX_MS;
      if (moved && fast && Math.abs(dx) >= SWIPE_COMMIT_PX) {
        if (dx > 0) _grade(2, 'right');     // Remembered
        else        _grade(0, 'left');      // Forgot
      } else {
        // Snap back — clearing the inline transform lets the CSS
        // transition animate the card to centre.
        $card.style.transform = '';
        if (!moved) {
          // True tap (no significant movement) → flip the card.
          _flipCard();
        }
      }
    }

    $card.addEventListener('touchstart', onStart, { passive: true });
    $card.addEventListener('touchmove', onMove, { passive: true });
    $card.addEventListener('touchend', onEnd);
    $card.addEventListener('touchcancel', () => {
      dragging = false;
      $card.style.transition = '';
      $card.style.transform = '';
    });

    // Mouse fallback for desktop dev — same protocol.
    $card.addEventListener('mousedown', (e) => {
      onStart(e);
      const onMM = (ev) => onMove(ev);
      const onMU = (ev) => {
        onEnd(ev);
        document.removeEventListener('mousemove', onMM);
        document.removeEventListener('mouseup', onMU);
      };
      document.addEventListener('mousemove', onMM);
      document.addEventListener('mouseup', onMU);
    });
  }

  // ── Boot ───────────────────────────────────────────────────────
  async function boot() {
    // 1. Resolve DOM handles.
    $root = _$('lx-mp-root');
    $progressCur = _$('lx-mp-progress-current');
    $progressTotal = _$('lx-mp-progress-total');
    $syncBtn = _$('lx-mp-sync-btn');
    $queueBadge = _$('lx-mp-queue-badge');
    $conn = _$('lx-mp-conn');
    $stage = _$('lx-mp-stage');
    $loading = _$('lx-mp-loading');
    $empty = _$('lx-mp-empty');
    $card = _$('lx-mp-card');
    $cardWord = _$('lx-mp-card-word');
    $cardState = _$('lx-mp-card-state');
    $cardTrans = _$('lx-mp-card-translations');
    $actionsRow = _$('lx-mp-actions-row');
    $forgotBtn = _$('lx-mp-forgot');
    $rememberedBtn = _$('lx-mp-remembered');
    $toast = _$('lx-mp-toast');
    $updateBanner = _$('lx-mp-update-banner');
    $updateRefresh = _$('lx-mp-update-refresh');

    // 2. Wire button handlers.
    if ($forgotBtn) $forgotBtn.addEventListener('click', () => _grade(0, 'left'));
    if ($rememberedBtn) $rememberedBtn.addEventListener('click', () => _grade(2, 'right'));
    if ($syncBtn) $syncBtn.addEventListener('click', () => _syncQueue());
    if ($card) _bindSwipe();
    if ($updateRefresh) {
      $updateRefresh.addEventListener('click', () => {
        if (state.waitingWorker) {
          state.waitingWorker.postMessage({ type: 'SKIP_WAITING' });
        } else {
          window.location.reload();
        }
      });
    }

    // 3. Connection listeners.
    window.addEventListener('online', () => _setOnline(true));
    window.addEventListener('offline', () => _setOnline(false));
    _setOnline(navigator.onLine);   // initial paint

    // 4. SW registration (non-blocking; failure is non-fatal).
    _registerServiceWorker();

    // 5. DB init.
    if (!NS.db) {
      console.error('[lexora.mobile] lexora.db missing — load order wrong?');
      _hide($loading);
      _toast('error', 'Database layer failed to load');
      return;
    }
    const initRes = await NS.db.init();
    if (!initRes.ok) {
      _hide($loading);
      _toast('error', 'Offline storage unavailable (' + initRes.error + ')');
      return;
    }

    // 6. Hydrate. If IDB is empty (first run), seed from the JSON
    //    the server injected; otherwise load whatever IDB has.
    const stats = await NS.db.stats();
    if (stats.ok && stats.cardCount === 0) {
      const initial = _readInitialCards();
      if (initial.length) {
        await NS.db.replaceCardsToReview(initial);
      }
    }

    // 7. Pull the due-card slice into memory.
    const due = await NS.db.getDueCards({ asOf: new Date() });
    state.cards = (due.ok && due.cards) ? due.cards : _readInitialCards();
    state.index = 0;

    _hide($loading);
    _renderCurrent();
    _refreshQueueBadge();

    // 8. Best-effort background prefetch + initial queue drain.
    if (state.online) {
      _syncQueue();
      _prefetchBatch();
    }
  }

  // ── Public API ─────────────────────────────────────────────────
  NS.mobile.boot = boot;

  // Auto-boot on DOM ready. The QWeb template orders the script tags
  // (vendor idb → lexora_db → mobile_practice) so by the time we run
  // window.lexora.db is available.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
