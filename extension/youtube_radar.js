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
  const _OVERLAY_HOST_ID = 'lx-radar-shadow-host';
  const _OVERLAY_STYLES_ID = 'lx-radar-host-styles';

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

  // ── Overlay state (S5) ──
  let _overlayHost          = null;   // top-level Shadow DOM host element
  let _overlayOpen          = false;  // gates re-fire while a card is up
  let _externalPlayHandler  = null;   // {video, fn} bound to detect YT-play
  let _radarDragInitialised = false;  // converts bottom/transform → top/left on first drag

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

  // ── Overlay UI (S5) ─────────────────────────────────────────────────────

  function _escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * Wrap exact-case occurrences of `word` within `cueText` in <mark>.
   * Falls back to plain-escaped cue if the word isn't found (e.g. our
   * matcher accepted a sliding-window hit but the original casing
   * doesn't line up cleanly — unlikely with our lowercase-normalised
   * tokenisation, but defensive).
   */
  function _highlightWord(cueText, word) {
    const safeCue = _escHtml(cueText);
    if (!word) return safeCue;
    const safeWord = _escHtml(word);
    const escapedRe = safeWord.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    // \b doesn't work cleanly with Unicode word boundaries in JS — use
    // lookahead/behind for ASCII-letter boundaries; in practice good
    // enough for visualising the match in a glassmorphism card.
    const re = new RegExp('(' + escapedRe + ')', 'gi');
    return safeCue.replace(re, '<mark class="lx-radar-mark">$1</mark>');
  }

  // Embedded CSS — same pattern as M27 _REVIEW_CSS / M28 _QL_CSS / M33
  // _RADAR_CSS (M33 audio shadow had a different palette). All structural
  // flex / overflow props carry !important per the M28-12d rule —
  // YouTube's own stylesheet will fight us otherwise.
  const _RADAR_HOST_CSS = `
    #${_OVERLAY_HOST_ID} {
      position: fixed !important;
      bottom: 24px !important;
      left: 50% !important;
      transform: translateX(-50%) !important;
      z-index: 2147483600 !important;
      width: 380px !important;
      max-width: calc(100vw - 32px) !important;
      pointer-events: auto !important;
      font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    }
  `;

  const _RADAR_SHADOW_CSS = `
    :host { all: initial; }
    *, *::before, *::after { box-sizing: border-box; }

    .lx-radar-card {
      display: flex !important;
      flex-direction: column !important;
      max-height: 70vh !important;
      background: rgba(15, 23, 42, 0.94);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      border: 1px solid rgba(20, 184, 166, 0.55);
      border-radius: 14px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.55),
                  0 0 0 1px rgba(20, 184, 166, 0.15);
      color: #f1f5f9;
      font-size: 13px;
      line-height: 1.45;
      overflow: hidden !important;
    }

    .lx-radar-header {
      flex-shrink: 0 !important;
      display: flex !important;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      background: linear-gradient(90deg,
        rgba(20, 184, 166, 0.32),
        rgba(245, 158, 11, 0.22));
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      cursor: move;
      user-select: none;
      -webkit-user-select: none;
    }
    .lx-radar-header-icon { font-size: 16px; }
    .lx-radar-header-title {
      flex: 1 1 auto;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #ccfbf1;
    }
    .lx-radar-header-hint {
      font-size: 10px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.45);
      text-transform: none;
      letter-spacing: 0;
    }
    .lx-radar-close-btn {
      flex-shrink: 0;
      width: 22px;
      height: 22px;
      padding: 0;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 6px;
      color: #f1f5f9;
      font-size: 13px;
      line-height: 1;
      cursor: pointer;
    }
    .lx-radar-close-btn:hover { background: rgba(255, 255, 255, 0.18); }

    .lx-radar-scroll {
      flex: 1 1 auto !important;
      min-height: 0 !important;
      overflow-y: auto !important;
      padding: 14px 16px 12px;
    }

    .lx-radar-word {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0.01em;
      color: #f1f5f9;
      margin-bottom: 8px;
      word-break: break-word;
    }

    .lx-radar-trans {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 10px;
    }
    .lx-radar-trans-row {
      display: flex;
      align-items: baseline;
      gap: 8px;
      font-size: 13px;
      color: #f1f5f9;
    }
    .lx-radar-flag { font-size: 13px; opacity: 0.95; flex-shrink: 0; }
    .lx-radar-trans-text {
      color: rgba(255, 255, 255, 0.92);
      word-break: break-word;
    }
    .lx-radar-trans-empty {
      font-style: italic;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.4);
    }

    .lx-radar-cue {
      margin-top: 8px;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.04);
      border-left: 3px solid rgba(20, 184, 166, 0.55);
      border-radius: 4px;
      font-size: 12px;
      font-style: italic;
      color: rgba(255, 255, 255, 0.82);
      word-break: break-word;
    }
    .lx-radar-mark {
      background: rgba(245, 158, 11, 0.32);
      color: #fde68a;
      padding: 0 2px;
      border-radius: 2px;
      font-weight: 600;
      font-style: normal;
    }

    .lx-radar-footer {
      flex-shrink: 0 !important;
      display: grid !important;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      padding: 10px 12px 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(0, 0, 0, 0.2);
    }
    .lx-radar-btn {
      padding: 8px 10px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      color: #f1f5f9;
      background: rgba(255, 255, 255, 0.06);
      transition: background 0.12s ease, transform 0.08s ease;
    }
    .lx-radar-btn:hover  { background: rgba(255, 255, 255, 0.14); }
    .lx-radar-btn:active { transform: translateY(1px); }

    .lx-radar-btn-primary {
      grid-column: 1 / 3;
      background: linear-gradient(90deg, #14b8a6, #0d9488);
      border-color: rgba(20, 184, 166, 0.55);
      color: #ffffff;
    }
    .lx-radar-btn-primary:hover {
      background: linear-gradient(90deg, #2dd4bf, #14b8a6);
    }

    .lx-radar-btn-skip   { border-color: rgba(245, 158, 11, 0.45); color: #fde68a; }
    .lx-radar-btn-skip:hover   { background: rgba(245, 158, 11, 0.18); }
    .lx-radar-btn-kill   { border-color: rgba(239, 68, 68, 0.40); color: #fca5a5; }
    .lx-radar-btn-kill:hover   { background: rgba(239, 68, 68, 0.18); }
  `;

  function _ensureRadarStyles() {
    if (document.getElementById(_OVERLAY_STYLES_ID)) return;
    const style = document.createElement('style');
    style.id = _OVERLAY_STYLES_ID;
    style.textContent = _RADAR_HOST_CSS;
    (document.head || document.documentElement).appendChild(style);
  }

  function _renderRadarOverlay(hit, video) {
    if (_overlayOpen) return;            // belt+braces; tick guards too
    _ensureRadarStyles();
    _closeOverlayDom();                  // remove any stale leftover host

    const host = document.createElement('div');
    host.id = _OVERLAY_HOST_ID;
    (document.body || document.documentElement).appendChild(host);
    const shadow = host.attachShadow({ mode: 'open' });

    const translations = (hit.entry && hit.entry.translations) || {};
    const transRows = [];
    const FLAGS = { en: '🇬🇧', uk: '🇺🇦', el: '🇬🇷', pl: '🇵🇱' };
    // Show every non-source language we have a translation for.
    const order = ['uk', 'el', 'pl', 'en'].filter(
      (l) => l !== hit.entry.lang && translations[l],
    );
    for (const lang of order) {
      transRows.push(
        `<div class="lx-radar-trans-row">
           <span class="lx-radar-flag">${_escHtml(FLAGS[lang] || lang)}</span>
           <span class="lx-radar-trans-text">${_escHtml(translations[lang])}</span>
         </div>`
      );
    }
    const transBlock = transRows.length
      ? `<div class="lx-radar-trans">${transRows.join('')}</div>`
      : '<div class="lx-radar-trans-empty">No translations on file for this entry.</div>';

    const cueHtml = _highlightWord(hit.cueText || '', hit.word);

    shadow.innerHTML = `
      <style>${_RADAR_SHADOW_CSS}</style>
      <div class="lx-radar-card" role="dialog" aria-label="Lexora Radar — word in your vocabulary">
        <div class="lx-radar-header" data-lx-drag>
          <span class="lx-radar-header-icon" aria-hidden="true">📡</span>
          <div class="lx-radar-header-title">
            Lexora Radar
            <div class="lx-radar-header-hint">Word from your vocabulary</div>
          </div>
          <button class="lx-radar-close-btn" id="lx-radar-x" aria-label="Continue playing">✕</button>
        </div>

        <div class="lx-radar-scroll">
          <div class="lx-radar-word">${_escHtml(hit.word)}</div>
          ${transBlock}
          <div class="lx-radar-cue">${cueHtml}</div>
        </div>

        <div class="lx-radar-footer">
          <button id="lx-radar-rewind" class="lx-radar-btn lx-radar-btn-primary">
            ⏪ Rewind 5 s &amp; Play
          </button>
          <button id="lx-radar-continue" class="lx-radar-btn">▶ Continue</button>
          <button id="lx-radar-skip"     class="lx-radar-btn lx-radar-btn-skip">🔕 Skip this word</button>
          <button id="lx-radar-kill"     class="lx-radar-btn lx-radar-btn-kill" style="grid-column: 1 / 3;">
            ✖ Disable radar for this video
          </button>
        </div>
      </div>
    `;

    // ── Bind button handlers ─────────────────────────────────────────────
    const $ = (sel) => shadow.querySelector(sel);

    $('#lx-radar-x').addEventListener('click', () => {
      // Top-right ✕ = same semantics as ▶ Continue: dismiss + resume.
      _onContinue(video);
    });
    $('#lx-radar-rewind').addEventListener('click', () => _onRewindAndPlay(video));
    $('#lx-radar-continue').addEventListener('click', () => _onContinue(video));
    $('#lx-radar-skip').addEventListener('click', () => _onSkipWord(hit.word, video));
    $('#lx-radar-kill').addEventListener('click', () => _onDisableForVideo(video));

    _makeRadarDraggable(host, shadow);
    _bindExternalPlayDetection(video);

    _overlayHost = host;
    _overlayOpen = true;
  }

  // ── Button actions ──────────────────────────────────────────────────────

  function _onRewindAndPlay(video) {
    if (video) {
      try {
        const t = Math.max(0, (video.currentTime || 0) - 5);
        video.currentTime = t;
      } catch (e) {}
    }
    _closeOverlay();
    _safePlay(video);
  }

  function _onContinue(video) {
    _closeOverlay();
    _safePlay(video);
  }

  function _onSkipWord(word, video) {
    if (word) _tabSkip.add(_normToken(word));
    console.log(_LOG_PREFIX + ' skipping %o for this tab (%d skipped total)',
      _LOG_STYLE, word, _tabSkip.size);
    _closeOverlay();
    _safePlay(video);
  }

  function _onDisableForVideo(video) {
    _videoKillSwitch = true;
    console.log(_LOG_PREFIX + ' radar disabled for this video (kill switch on)', _LOG_STYLE);
    _closeOverlay();
    _safePlay(video);
  }

  function _safePlay(video) {
    if (!video) return;
    try {
      const p = video.play();
      // Some browsers return a Promise that can reject if autoplay is
      // gated. We requested this play in response to a user click, so
      // it should be fine, but swallow any reject just in case.
      if (p && typeof p.catch === 'function') p.catch(() => {});
    } catch (e) {}
  }

  // ── Close overlay (cooldown advances HERE per sub-decision 34c) ─────────

  function _closeOverlayDom() {
    // Idempotent DOM removal — does NOT touch cooldown / open flag.
    const existing = document.getElementById(_OVERLAY_HOST_ID);
    if (existing) {
      try { existing.remove(); } catch (e) {}
    }
    _overlayHost = null;
    _radarDragInitialised = false;
  }

  function _closeOverlay() {
    if (!_overlayOpen) {
      _closeOverlayDom();
      return;
    }
    _unbindExternalPlayDetection();
    _closeOverlayDom();
    _overlayOpen = false;
    // CRITICAL (sub-decision 34c): cooldown timer starts at close, not
    // at fire. The user can read the alert at their own pace; the
    // 120 s clock only starts ticking once they dismiss it.
    _lastFiredAt = performance.now();
    console.log(_LOG_PREFIX + ' overlay closed; cooldown timer started (%ds)',
      _LOG_STYLE, Math.round(_cooldownMs / 1000));
  }

  // ── External-play detection ─────────────────────────────────────────────
  // The user can hit YouTube's own play button (or press space, or click the
  // video surface). In those cases we want the overlay to close too so it
  // doesn't linger over a playing video. We bind a 'play' listener on the
  // <video> at render time and tear it down on close — our own _safePlay
  // calls always close FIRST, so they never see the listener.

  function _bindExternalPlayDetection(video) {
    if (!video) return;
    const fn = () => {
      if (_overlayOpen) {
        console.log(_LOG_PREFIX + ' external play detected — closing overlay', _LOG_STYLE);
        _closeOverlay();
      }
    };
    try { video.addEventListener('play', fn); } catch (e) { return; }
    _externalPlayHandler = { video, fn };
  }

  function _unbindExternalPlayDetection() {
    if (!_externalPlayHandler) return;
    try {
      _externalPlayHandler.video.removeEventListener('play', _externalPlayHandler.fn);
    } catch (e) {}
    _externalPlayHandler = null;
  }

  // ── Draggable header (M28-17 pattern, viewport-clamped) ─────────────────

  function _makeRadarDraggable(host, shadow) {
    const header = shadow.querySelector('[data-lx-drag]');
    if (!header) return;
    let dragging = false;
    let startX = 0, startY = 0;
    let hostStartLeft = 0, hostStartTop = 0;

    function onDown(e) {
      // Ignore drags that start on a button inside the header.
      if (e.target && e.target.closest && e.target.closest('button')) return;
      dragging = true;

      // First drag: convert from bottom+translateX(-50%) to top/left so
      // we have a single set of coordinates to mutate.
      if (!_radarDragInitialised) {
        const rect = host.getBoundingClientRect();
        host.style.setProperty('top',       rect.top + 'px',  'important');
        host.style.setProperty('left',      rect.left + 'px', 'important');
        host.style.setProperty('bottom',    'auto',           'important');
        host.style.setProperty('transform', 'none',           'important');
        _radarDragInitialised = true;
      }
      const r = host.getBoundingClientRect();
      hostStartLeft = r.left;
      hostStartTop  = r.top;
      startX = e.clientX;
      startY = e.clientY;
      e.preventDefault();

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup',   onUp);
    }
    function onMove(e) {
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const rect = host.getBoundingClientRect();
      const maxLeft = Math.max(0, window.innerWidth  - rect.width);
      const maxTop  = Math.max(0, window.innerHeight - rect.height);
      const nl = Math.min(maxLeft, Math.max(0, hostStartLeft + dx));
      const nt = Math.min(maxTop,  Math.max(0, hostStartTop  + dy));
      host.style.setProperty('left', nl + 'px', 'important');
      host.style.setProperty('top',  nt + 'px', 'important');
    }
    function onUp() {
      dragging = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup',   onUp);
    }
    header.addEventListener('mousedown', onDown);
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

    if (_overlayOpen) return;                  // already paused + showing UI
    if (!_masterEnabled || _videoKillSwitch || !_radarHits.length) return;
    if (now - _lastFiredAt < _cooldownMs) return;

    const currentMs = (_currentVideo.currentTime || 0) * 1000;
    const idx = _findNextHitIndex(currentMs);
    if (idx === -1) return;
    if (idx === _lastFiredIdx) return;         // already fired on this very hit

    const hit = _radarHits[idx];
    const delta = hit.atMs - currentMs;
    if (delta > _lookaheadMs) return;          // not in the look-ahead window yet
    if (_tabSkip.has(_normToken(hit.word))) return;

    // FIRE 🎯
    _lastFiredIdx = idx;
    // NOTE (sub-decision 34c): cooldown timer does NOT advance here in
    // S5 — it's advanced inside _closeOverlay() so the user gets a full
    // 120 s of breathing room AFTER they dismiss the alert. The
    // _overlayOpen flag above prevents re-fire while the card is up.
    try { _currentVideo.pause(); } catch (e) {}

    console.log(_LOG_PREFIX + ' HIT! word=%o at=%dms (Δ%dms) cue=%o',
      _LOG_STYLE, hit.word, hit.atMs, Math.round(delta), hit.cueText);

    _renderRadarOverlay(hit, _currentVideo);
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
    // Tear down any open overlay first so it doesn't linger over the
    // next video; this also unbinds the external-play listener from the
    // old <video> element which is about to be replaced.
    if (_overlayOpen) {
      _unbindExternalPlayDetection();
      _closeOverlayDom();
      _overlayOpen = false;
    }
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
