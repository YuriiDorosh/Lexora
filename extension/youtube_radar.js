/**
 * extension/youtube_radar.js — M34 YouTube Vocab Radar (scanner state machine)
 *
 * Sibling of extension/overlay.js (the M24 click-on-subtitle Quick Look).
 * Runs in the extension's ISOLATED world on www.youtube.com pages.
 *
 * Responsibilities:
 *   1. Inject extension/youtube_radar_inject.js into the page's MAIN world
 *      (idempotent — survives SPA navigation).
 *   2. Fetch the user's vocabulary via chrome.storage.local.lx_radar_vocab_cache
 *      with a 15-min TTL; on miss / stale, sends 'lexora-get-my-vocab' to the
 *      background service worker (M34-S2) and re-caches.
 *   3. Build a vocabulary index — single-token Map<normalized, entry> plus a
 *      sorted-descending-by-token-count list of multi-word phrases for the
 *      longest-match sliding window.
 *   4. Listen for window.postMessage({source:'lx-radar', type:'cues', cues})
 *      from the inject script. Tokenise every cue, run the longest-match
 *      sliding window (3-gram → 2-gram → 1-gram). First hit per cue wins.
 *      Sort hits by atMs ascending → _radarHits.
 *   5. On <video>.timeupdate (throttled 250 ms): binary-search _radarHits for
 *      the next upcoming atMs, check lookahead window + cooldown + per-tab
 *      skip set + per-video kill switch + master toggle. If eligible: pause
 *      the video and console.log the hit. (Overlay UI lands in S5.)
 *   6. On yt-navigate-finish (YouTube SPA event): reset _radarHits,
 *      _videoKillSwitch, _tabSkip, _lastFiredIdx — re-attach to the new video.
 *
 * See ADR-033 for architecture decisions; PLAN §M34 for the spec.
 */

(function () {
  'use strict';

  if (location.hostname !== 'www.youtube.com') return;
  if (window.__lxRadarContentLoaded) return;
  window.__lxRadarContentLoaded = true;

  // ── Constants & state ───────────────────────────────────────────────────

  const _LOG_PREFIX = '%c[lx-radar]';
  const _LOG_STYLE  = 'color:#14b8a6;font-weight:bold';
  const _CACHE_TTL_MS = 15 * 60 * 1000;
  const _TICK_THROTTLE_MS = 250;
  const _VIDEO_POLL_MS = 500;
  const _VIDEO_POLL_MAX_TRIES = 120;            // 60 s of polling
  const _INJECT_ATTR = 'data-lx-radar-inject';
  const _INJECT_FILE = 'youtube_radar_inject.js';

  // Same Unicode-aware token regex used by M27 + M33, broadened to also cover
  // polytonic Greek (ἀ-῿) so old transcript pages still tokenise correctly.
  const _WORD_TOKEN_RE = /[\wÀ-ɏͰ-Ͽἀ-῿Ѐ-ӿ'\-]+/gu;

  // Defaults; overwritten by chrome.storage.sync on _loadSettings() and on
  // every onChanged event (M34-S6 surfaces these in the Options page).
  let _masterEnabled = true;
  let _cooldownMs    = 120 * 1000;
  let _lookaheadMs   = 4 * 1000;

  // Hit timeline + tick bookkeeping.
  let _radarHits     = [];      // sorted by atMs ascending
  let _latestCues    = null;    // last cue array received from the inject script
  let _vocabIndex    = null;    // { wordMap: Map<norm, entry>, phrases: [{tokens, entry}] }
  let _lastFiredAt   = -Infinity;  // performance.now() of last fire; sentinel so the
                                   // first fire isn't gated by the cooldown timer on
                                   // a brand-new page (performance.now() − 0 would be
                                   // a small number → false cooldown for ~120 s).
  let _lastFiredIdx  = -1;      // index in _radarHits — prevents refiring the same hit
  let _lastTickMs    = 0;
  const _tabSkip       = new Set();   // lowercased words skipped for this page lifetime
  let _videoKillSwitch = false;
  let _currentVideo    = null;
  let _videoPollIv     = null;

  // ── Tokenisation & normalisation ────────────────────────────────────────

  function _normToken(t) {
    return String(t || '').normalize('NFC').toLowerCase();
  }

  function _tokenize(text) {
    if (!text) return [];
    const tokens = [];
    _WORD_TOKEN_RE.lastIndex = 0;
    let m;
    while ((m = _WORD_TOKEN_RE.exec(text)) !== null) {
      tokens.push(_normToken(m[0]));
    }
    return tokens;
  }

  // ── Vocab cache + index ─────────────────────────────────────────────────

  async function _getVocab() {
    // 1. Try the cache first.
    let payload = null;
    try {
      const stored = await chrome.storage.local.get('lx_radar_vocab_cache');
      payload = stored && stored.lx_radar_vocab_cache;
    } catch (e) {
      console.warn('[lx-radar] storage read failed:', e);
    }

    const fresh = payload &&
      payload.status === 'ok' &&
      Array.isArray(payload.words) &&
      typeof payload.generated_at === 'number' &&
      (Date.now() - payload.generated_at * 1000) < _CACHE_TTL_MS;

    if (fresh) {
      console.log(_LOG_PREFIX + ' vocab cache HIT (%d words, age %ds)',
        _LOG_STYLE, payload.words.length,
        Math.round((Date.now() - payload.generated_at * 1000) / 1000));
      return payload.words;
    }

    // 2. Miss / stale — ask background to fetch fresh & re-cache.
    try {
      const resp = await chrome.runtime.sendMessage({ action: 'lexora-get-my-vocab' });
      if (resp && resp.status === 'ok' && Array.isArray(resp.words)) {
        console.log(_LOG_PREFIX + ' vocab fetched fresh (%d words)',
          _LOG_STYLE, resp.words.length);
        return resp.words;
      }
      if (resp && resp.status === 'unauthorized') {
        console.warn('[lx-radar] not authenticated — radar disabled. ' +
                     'Log in to Lexora and reload the page.');
        return [];
      }
      console.warn('[lx-radar] unexpected vocab response:', resp);
    } catch (e) {
      console.warn('[lx-radar] vocab fetch failed:', e);
    }
    return [];
  }

  function _buildIndex(words) {
    const wordMap = new Map();
    const phrases = [];
    for (const w of words || []) {
      const source = w && (w.normalized || w.word) || '';
      const tokens = _tokenize(source);
      if (!tokens.length) continue;
      if (tokens.length === 1) {
        // First write wins — vocab is ordered write_date desc on the server
        // so a recent duplicate doesn't displace the canonical entry.
        if (!wordMap.has(tokens[0])) wordMap.set(tokens[0], w);
      } else {
        phrases.push({ tokens, entry: w });
      }
    }
    // Longest first — sliding window in _findCueHit checks longer N-grams
    // before single tokens, so "kick the bucket" beats "kick" when both
    // are in the vocab.
    phrases.sort((a, b) => b.tokens.length - a.tokens.length);
    return { wordMap, phrases };
  }

  // ── Cue → hit mapping (longest-match sliding window) ────────────────────

  function _findCueHit(cueText, idx) {
    const tokens = _tokenize(cueText);
    if (!tokens.length) return null;

    // Phrases pass: phrases is sorted desc by token count, so the first
    // match we accept is the longest possible.
    for (const phrase of idx.phrases) {
      const plen = phrase.tokens.length;
      if (plen > tokens.length) continue;
      for (let i = 0; i + plen <= tokens.length; i++) {
        let match = true;
        for (let j = 0; j < plen; j++) {
          if (tokens[i + j] !== phrase.tokens[j]) { match = false; break; }
        }
        if (match) {
          return { word: phrase.entry.word, entry: phrase.entry };
        }
      }
    }

    // Single-token fallback — first hit wins per cue.
    for (const tok of tokens) {
      const entry = idx.wordMap.get(tok);
      if (entry) return { word: entry.word, entry };
    }
    return null;
  }

  function _rebuildHits() {
    if (!_vocabIndex || !_latestCues) return;
    const hits = [];
    for (const cue of _latestCues) {
      if (!cue || typeof cue.startMs !== 'number') continue;
      const found = _findCueHit(cue.text, _vocabIndex);
      if (found) {
        hits.push({
          atMs:     cue.startMs,
          word:     found.word,
          entry:    found.entry,
          cueText:  cue.text,
          cueEndMs: typeof cue.endMs === 'number' ? cue.endMs : cue.startMs,
        });
      }
    }
    hits.sort((a, b) => a.atMs - b.atMs);
    _radarHits = hits;
    _lastFiredIdx = -1;
    console.log(_LOG_PREFIX + ' hit timeline rebuilt: %d hits over %d cues',
      _LOG_STYLE, hits.length, _latestCues.length);
  }

  // ── Settings (chrome.storage.sync) ──────────────────────────────────────

  async function _loadSettings() {
    try {
      const s = await chrome.storage.sync.get([
        'lexora_radar_enabled',
        'lexora_radar_cooldown_seconds',
        'lexora_radar_lookahead_seconds',
      ]);
      // Default ON when the key is absent (matches the M34-S6 contract).
      _masterEnabled = s.lexora_radar_enabled !== false;
      const c = Number(s.lexora_radar_cooldown_seconds);
      if (isFinite(c) && c >= 10) _cooldownMs = c * 1000;
      const la = Number(s.lexora_radar_lookahead_seconds);
      if (isFinite(la) && la >= 1) _lookaheadMs = la * 1000;
      console.log(_LOG_PREFIX + ' settings: enabled=%s cooldown=%ds lookahead=%ds',
        _LOG_STYLE, _masterEnabled,
        Math.round(_cooldownMs / 1000), Math.round(_lookaheadMs / 1000));
    } catch (e) {
      console.warn('[lx-radar] settings load failed; defaults stand:', e);
    }
  }

  function _attachStorageChangeListener() {
    try {
      chrome.storage.onChanged.addListener((changes, area) => {
        if (area !== 'sync') return;
        if ('lexora_radar_enabled' in changes) {
          _masterEnabled = changes.lexora_radar_enabled.newValue !== false;
          console.log(_LOG_PREFIX + ' master toggle → %s', _LOG_STYLE, _masterEnabled);
        }
        if ('lexora_radar_cooldown_seconds' in changes) {
          const v = Number(changes.lexora_radar_cooldown_seconds.newValue);
          if (isFinite(v) && v >= 10) {
            _cooldownMs = v * 1000;
            console.log(_LOG_PREFIX + ' cooldown → %ds', _LOG_STYLE, v);
          }
        }
        if ('lexora_radar_lookahead_seconds' in changes) {
          const v = Number(changes.lexora_radar_lookahead_seconds.newValue);
          if (isFinite(v) && v >= 1) {
            _lookaheadMs = v * 1000;
            console.log(_LOG_PREFIX + ' lookahead → %ds', _LOG_STYLE, v);
          }
        }
      });
    } catch (e) {
      // ignore — onChanged is non-critical
    }
  }

  // ── Inject main-world script ────────────────────────────────────────────

  function _injectMainWorld() {
    try {
      if (document.querySelector('script[' + _INJECT_ATTR + ']')) return;
      const script = document.createElement('script');
      script.src = chrome.runtime.getURL(_INJECT_FILE);
      script.setAttribute(_INJECT_ATTR, '1');
      script.onload = function () {
        // Once the main-world IIFE has run, the <script> tag is just dead
        // DOM weight — remove it. The patches live on, but the inject
        // script's own window.__lxRadarInjected guard makes re-loads safe.
        try { script.remove(); } catch (e) {}
      };
      (document.head || document.documentElement).appendChild(script);
    } catch (e) {
      console.warn('[lx-radar] main-world inject failed:', e);
    }
  }

  // ── Message listener for cues + ready ────────────────────────────────────

  function _attachMessageListener() {
    window.addEventListener('message', (e) => {
      // Only accept messages from THIS window — the inject script
      // postMessages with target '*' but e.source is always the current
      // window when it's posting to itself.
      if (e.source !== window) return;
      const d = e.data;
      if (!d || typeof d !== 'object' || d.source !== 'lx-radar') return;

      if (d.type === 'ready') {
        console.log(_LOG_PREFIX + ' inject ready (patches landed)', _LOG_STYLE);
        return;
      }
      if (d.type === 'cues' && Array.isArray(d.cues)) {
        _latestCues = d.cues;
        _rebuildHits();
      }
    });
  }

  // ── Scanner tick ────────────────────────────────────────────────────────

  function _findNextHitIndex(currentMs) {
    // Binary search for the smallest index where atMs > currentMs.
    let lo = 0, hi = _radarHits.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (_radarHits[mid].atMs <= currentMs) lo = mid + 1;
      else hi = mid;
    }
    return lo < _radarHits.length ? lo : -1;
  }

  function _onTimeUpdate() {
    if (!_currentVideo) return;
    const now = performance.now();
    if (now - _lastTickMs < _TICK_THROTTLE_MS) return;
    _lastTickMs = now;

    if (!_masterEnabled || _videoKillSwitch || !_radarHits.length) return;
    if (now - _lastFiredAt < _cooldownMs) return;

    const currentMs = (_currentVideo.currentTime || 0) * 1000;
    const idx = _findNextHitIndex(currentMs);
    if (idx === -1) return;
    if (idx === _lastFiredIdx) return;     // already paused on this very hit

    const hit = _radarHits[idx];
    const delta = hit.atMs - currentMs;
    if (delta > _lookaheadMs) return;       // not in the look-ahead window yet
    if (_tabSkip.has(_normToken(hit.word))) return;

    // FIRE 🎯
    _lastFiredIdx = idx;
    // NOTE: S4-only contract — advance _lastFiredAt at fire time so the
    // cooldown timer starts now. S5 will move this advance to the
    // overlay-close handler so the user gets a full cooldown after they
    // dismiss the alert (sub-decision 34c).
    _lastFiredAt = now;
    try { _currentVideo.pause(); } catch (e) {}

    console.log(_LOG_PREFIX + ' HIT! word=%o at=%dms (Δ%dms) cue=%o',
      _LOG_STYLE, hit.word, hit.atMs, Math.round(delta), hit.cueText);
  }

  // ── Video element attachment + polling ──────────────────────────────────

  function _findVideo() {
    return document.querySelector('video.html5-main-video')
        || document.querySelector('video');
  }

  function _attachToVideo(video) {
    if (!video || video === _currentVideo) return;
    if (_currentVideo) {
      try { _currentVideo.removeEventListener('timeupdate', _onTimeUpdate); } catch (e) {}
    }
    _currentVideo = video;
    video.addEventListener('timeupdate', _onTimeUpdate);
    console.log(_LOG_PREFIX + ' attached to <video>', _LOG_STYLE);
  }

  function _bootVideoWatch() {
    if (_videoPollIv) { clearInterval(_videoPollIv); _videoPollIv = null; }
    const v = _findVideo();
    if (v) { _attachToVideo(v); return; }
    let tries = 0;
    _videoPollIv = setInterval(() => {
      tries++;
      const vv = _findVideo();
      if (vv) { _attachToVideo(vv); clearInterval(_videoPollIv); _videoPollIv = null; }
      else if (tries >= _VIDEO_POLL_MAX_TRIES) {
        clearInterval(_videoPollIv);
        _videoPollIv = null;
        console.warn('[lx-radar] gave up waiting for <video> after %ds',
          Math.round(_VIDEO_POLL_MAX_TRIES * _VIDEO_POLL_MS / 1000));
      }
    }, _VIDEO_POLL_MS);
  }

  // ── SPA navigation reset ────────────────────────────────────────────────

  function _onYtNavigate() {
    console.log(_LOG_PREFIX + ' yt-navigate-finish — resetting state', _LOG_STYLE);
    _radarHits       = [];
    _latestCues      = null;
    _videoKillSwitch = false;
    _tabSkip.clear();
    _lastFiredAt     = -Infinity;
    _lastFiredIdx    = -1;
    _lastTickMs      = 0;
    // The current <video> element is usually replaced on nav. Re-find +
    // re-attach. The inject script's __lxRadarInjected guard means the
    // main-world patches survive — we don't need to re-inject.
    _bootVideoWatch();
    // Ensure inject is present on hard reloads where the page DOM was wiped.
    _injectMainWorld();
  }

  // ── Bootstrap ───────────────────────────────────────────────────────────

  async function _init() {
    console.log(_LOG_PREFIX + ' youtube_radar.js init on %s', _LOG_STYLE, location.href);

    _attachMessageListener();
    _attachStorageChangeListener();
    window.addEventListener('yt-navigate-finish', _onYtNavigate);

    await _loadSettings();

    // Build vocab index in parallel with the main-world inject — cues from
    // the inject can arrive before vocab; _rebuildHits short-circuits until
    // both are ready.
    _injectMainWorld();
    _bootVideoWatch();

    const words = await _getVocab();
    _vocabIndex = _buildIndex(words);
    console.log(_LOG_PREFIX + ' vocab index: %d singles + %d phrases',
      _LOG_STYLE, _vocabIndex.wordMap.size, _vocabIndex.phrases.length);
    _rebuildHits();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }
})();
