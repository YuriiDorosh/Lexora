'use strict';

// ---------------------------------------------------------------------------
// M24 — YouTube Subtitle Overlay (fixed)
//
// Root-cause of the original failure:
//   YouTube sets pointer-events:none on .ytp-caption-window-container and
//   its children so that clicks pass through to the video player beneath.
//   This script forces pointer-events:auto back on the container + segments,
//   then wraps each whitespace-delimited token in a clickable <span>.
//
// SPA navigation: YouTube fires 'yt-navigate-finish' when moving between
//   videos. We reconnect the caption observer on each navigation event.
// ---------------------------------------------------------------------------

const _OVERLAY_ID   = 'lx-yt-overlay';
const _WORD_CLASS   = 'lx-sub-word';
const _STYLES_ID    = 'lx-overlay-styles';

// Container selectors — tried in order; first match wins.
// YouTube changes these periodically; multiple fallbacks give robustness.
const _CONTAINER_SELECTORS = [
  '.ytp-caption-window-container',
  '.ytp-captions-container',
  '.captions-text',
];

// Broad player anchor — always present once the player renders.
// Used to attach the outer document observer early.
const _PLAYER_SELECTORS = [
  '#movie_player',
  'ytd-player',
  '.html5-video-player',
  '#player-container',
];

const _OVERLAY_CSS = `
  /* ── Force click-through fix ──────────────────────────── */
  .ytp-caption-window-container,
  .ytp-captions-container,
  .ytp-caption-segment,
  .captions-text {
    pointer-events: auto !important;
  }

  /* ── Interactive word spans ───────────────────────────── */
  .${_WORD_CLASS} {
    cursor: pointer !important;
    border-radius: 3px;
    border-bottom: 1px dashed rgba(129, 140, 248, 0.6) !important;
    transition: background 0.2s, color 0.2s;
    padding: 1px 1px;
    pointer-events: auto !important;
  }
  .${_WORD_CLASS}:hover {
    background: rgba(129, 140, 248, 0.25) !important;
    color: #818cf8 !important;
    outline: 1px solid rgba(129, 140, 248, 0.5);
  }

  /* ── Overlay card ─────────────────────────────────────── */
  #${_OVERLAY_ID} {
    position: fixed;
    bottom: 130px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999999;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    animation: lx-yt-fadein 0.25s ease;
    pointer-events: auto !important;
  }

  @keyframes lx-yt-fadein {
    from { opacity: 0; transform: translateX(-50%) translateY(14px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0); }
  }

  .lx-yt-card {
    min-width: 280px;
    max-width: 400px;
    max-height: 70vh !important;
    display: flex !important;
    flex-direction: column !important;
    background: rgba(10, 15, 30, 0.93);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 16px;
    box-shadow:
      0 16px 48px rgba(0,0,0,0.65),
      0 3px 10px rgba(0,0,0,0.45),
      inset 0 1px 0 rgba(255,255,255,0.08);
    overflow: hidden !important;
  }

  .lx-yt-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px 10px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    cursor: move;
    user-select: none;
  }

  .lx-yt-logo {
    flex-shrink: 0;
    width: 28px; height: 28px;
    border-radius: 7px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 800; color: #fff; letter-spacing: -0.5px;
  }

  .lx-yt-word {
    flex: 1;
    font-size: 15px; font-weight: 700;
    color: #e0e7ff; letter-spacing: 0.2px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; word-break: break-word;
  }

  .lx-yt-close {
    background: none; border: none;
    color: rgba(255,255,255,0.4); font-size: 18px;
    cursor: pointer !important; padding: 2px 6px;
    border-radius: 6px; line-height: 1;
    transition: color 0.15s, background 0.15s;
    pointer-events: auto !important;
  }
  .lx-yt-close:hover { color:#fff; background: rgba(255,255,255,0.1); }

  .lx-yt-body {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto !important;
    overflow: hidden !important;
    min-height: 0 !important;
    padding: 0;
  }

  .lx-yt-scroll {
    overflow-y: auto !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    padding: 10px 14px 6px;
    scrollbar-width: thin; scrollbar-color: rgba(99,102,241,0.4) transparent;
  }
  .lx-yt-scroll::-webkit-scrollbar { width: 4px; }
  .lx-yt-scroll::-webkit-scrollbar-track { background: transparent; }
  .lx-yt-scroll::-webkit-scrollbar-thumb {
    background: rgba(99,102,241,0.4); border-radius: 4px;
  }

  .lx-yt-footer {
    padding: 4px 14px 12px;
    border-top: 1px solid rgba(255,255,255,0.06);
    flex-shrink: 0 !important;
  }

  .lx-yt-loading {
    color: rgba(255,255,255,0.4); font-size: 13px;
    text-align: center; padding: 8px 0;
  }

  .lx-yt-translations { display:flex; flex-direction:column; gap:6px; margin-bottom:10px; }

  .lx-yt-translation { display:flex; align-items:baseline; gap:8px; }

  .lx-yt-lang-label {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    color: rgba(165,180,252,0.8); letter-spacing: 0.5px;
    flex-shrink: 0; min-width: 62px;
  }

  .lx-yt-trans-text { font-size:14px; font-weight:500; color:#f0f4ff; line-height:1.4; }

  .lx-yt-live-badge {
    font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
    color: #34d399; border: 1px solid rgba(52,211,153,0.5);
    border-radius: 4px; padding: 1px 4px; margin-left: 6px;
    flex-shrink: 0; align-self: center;
  }

  .lx-yt-no-def {
    font-size: 12px; color: rgba(255,255,255,0.38);
    font-style: italic; padding: 4px 0 8px;
  }

  .lx-yt-actions { display:flex; gap:8px; margin-top:0; }

  .lx-yt-add-btn {
    flex:1; padding:7px 12px;
    background: linear-gradient(135deg,#4f46e5,#7c3aed);
    border:none; border-radius:9px;
    color:#fff; font-size:12px; font-weight:600;
    cursor: pointer !important; pointer-events: auto !important;
    transition: opacity 0.15s, transform 0.1s;
  }
  .lx-yt-add-btn:hover { opacity:0.88; }
  .lx-yt-add-btn:active { transform:scale(0.97); }
  .lx-yt-add-btn:disabled { opacity:0.4; cursor:default !important; }

  .lx-yt-resume-btn {
    padding:7px 14px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius:9px; color:rgba(255,255,255,0.75);
    font-size:12px; font-weight:600;
    cursor: pointer !important; pointer-events: auto !important;
    transition: background 0.15s;
  }
  .lx-yt-resume-btn:hover { background:rgba(255,255,255,0.14); }

  .lx-yt-retry-btn {
    display:block; margin:8px auto 0;
    padding:6px 16px;
    background: rgba(99,102,241,0.2);
    border: 1px solid rgba(99,102,241,0.45);
    border-radius:9px; color:rgba(255,255,255,0.85);
    font-size:12px; font-weight:600;
    cursor: pointer !important; pointer-events: auto !important;
    transition: background 0.15s;
  }
  .lx-yt-retry-btn:hover { background:rgba(99,102,241,0.35); }

  .lx-yt-status {
    margin-top:7px; font-size:11px; font-weight:600;
    min-height:16px; text-align:center; color:rgba(255,255,255,0.55);
  }

  .lx-yt-explain-btn {
    display:block; width:100%; margin-top:6px; padding:6px 0;
    background: rgba(139,92,246,0.15);
    border: 1px solid rgba(139,92,246,0.4);
    border-radius:8px; color:#c4b5fd; font-size:12px; font-weight:600;
    cursor: pointer !important; pointer-events: auto !important;
    transition: background 0.15s;
  }
  .lx-yt-explain-btn:hover { background: rgba(139,92,246,0.3); }
  .lx-yt-explain-btn:disabled { opacity:0.5; cursor:default !important; }

  .lx-yt-grammar-block {
    display:none; margin-top:8px; padding:10px 12px;
    background: rgba(139,92,246,0.08);
    border-left: 3px solid #7c3aed;
    border-radius: 0 8px 8px 0;
    font-size:12px; line-height:1.6; color:#ddd6fe;
  }
  .lx-yt-grammar-block.lx-visible { display:block; }
`;

// ── Utilities ──────────────────────────────────────────────────────────────

function _injectStyles() {
  if (document.getElementById(_STYLES_ID)) return;
  const style = document.createElement('style');
  style.id = _STYLES_ID;
  style.textContent = _OVERLAY_CSS;
  (document.head || document.documentElement).appendChild(style);
  console.log('[Lexora] Overlay styles injected');
}

function _escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _getSubtitleLanguage() {
  const video = document.querySelector('video');
  if (!video) return 'en';
  for (const track of video.textTracks) {
    if (track.mode === 'showing') {
      return (track.language || '').slice(0, 2).toLowerCase() || 'en';
    }
  }
  return 'en';
}

// ── Word wrapping ──────────────────────────────────────────────────────────
//
// Root cause of prior failure: _wrapSegment() bailed if the target element
// had ANY child elements, but YouTube nests <span> tags inside caption
// segments for styling/timing. Switching to a TreeWalker that operates on
// raw TEXT NODES avoids the element-structure assumption entirely.

function _wrapTextNodes(root) {
  if (!root) return 0;

  // Collect text nodes that still need wrapping (snapshot before we mutate)
  const textNodes = [];
  const walker = document.createTreeWalker(
    root,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        // Already wrapped — skip
        if (parent.classList.contains(_WORD_CLASS)) return NodeFilter.FILTER_REJECT;
        // Inside our own overlay — skip
        if (parent.closest('#' + _OVERLAY_ID)) return NodeFilter.FILTER_REJECT;
        // Empty text — skip
        if (!node.textContent.trim()) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    }
  );

  let n;
  while ((n = walker.nextNode())) textNodes.push(n);

  let count = 0;
  for (const textNode of textNodes) {
    const text = textNode.textContent;
    if (!text.trim()) continue;

    const parts = text.split(/(\s+)/);
    const frag = document.createDocumentFragment();
    let hasWord = false;

    for (const part of parts) {
      if (!part) continue;
      if (/^\s+$/.test(part)) {
        frag.appendChild(document.createTextNode(part));
      } else {
        hasWord = true;
        const span = document.createElement('span');
        span.className = _WORD_CLASS;
        span.textContent = part;
        span.addEventListener('click', _onWordClick, { capture: true });
        frag.appendChild(span);
        count++;
      }
    }

    if (hasWord && textNode.parentNode) {
      textNode.parentNode.replaceChild(frag, textNode);
    }
  }

  return count;
}

function _processAllCaptionElements() {
  const container = _getContainer();
  if (!container) return;

  const count = _wrapTextNodes(container);
  if (count > 0) {
    console.log(`[Lexora] Wrapped ${count} subtitle word(s) into clickable spans`);
  }
}

// ── Extension-context guard ────────────────────────────────────────────────
//
// When the extension is reloaded while a YouTube tab remains open, the
// content script keeps running but chrome.runtime becomes invalid.
// Any chrome.runtime.sendMessage call then throws:
//   "Uncaught Error: Extension context invalidated."
//
// _sendMessage wraps sendMessage in a try-catch and checks chrome.runtime.id
// (undefined when context is invalidated) before calling. When invalidated,
// it invokes the callback with a typed sentinel so callers can show a
// "please refresh" hint instead of crashing.

function _isContextValid() {
  try {
    // chrome.runtime.id is undefined in an invalidated context
    return typeof chrome !== 'undefined' && !!chrome.runtime?.id;
  } catch (_) {
    return false;
  }
}

function _sendMessage(msg, callback) {
  if (!_isContextValid()) {
    console.warn('[Lexora] Extension context invalidated — refresh the tab to restore subtitle features.');
    callback && callback({ status: 'context_invalidated' });
    return;
  }
  try {
    chrome.runtime.sendMessage(msg, callback);
  } catch (err) {
    console.warn('[Lexora] sendMessage threw:', err.message);
    callback && callback({ status: 'context_invalidated' });
  }
}

// ── Overlay rendering ──────────────────────────────────────────────────────

function _removeOverlay() {
  document.getElementById(_OVERLAY_ID)?.remove();
}

// ── draggable card (YouTube overlay) ──────────────────────────────────────
// The overlay starts with bottom/transform CSS positioning; on first drag
// mousedown we convert to top/left so arithmetic stays straightforward.

function _makeDraggable(overlayEl) {
  const handle = overlayEl.querySelector('.lx-yt-card-header');
  if (!handle) return;

  let dragging = false, startX = 0, startY = 0, originLeft = 0, originTop = 0;

  handle.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    dragging = true;
    const rect = overlayEl.getBoundingClientRect();
    // Anchor to top/left so drag math is simple
    overlayEl.style.bottom    = 'auto';
    overlayEl.style.transform = 'none';
    overlayEl.style.left      = rect.left + 'px';
    overlayEl.style.top       = rect.top  + 'px';
    startX     = e.clientX;
    startY     = e.clientY;
    originLeft = rect.left;
    originTop  = rect.top;
    e.preventDefault();
    e.stopPropagation();
  });

  const onMove = (e) => {
    if (!dragging) return;
    const newLeft = Math.max(0, Math.min(window.innerWidth  - overlayEl.offsetWidth,  originLeft + e.clientX - startX));
    const newTop  = Math.max(0, Math.min(window.innerHeight - overlayEl.offsetHeight, originTop  + e.clientY - startY));
    overlayEl.style.left = newLeft + 'px';
    overlayEl.style.top  = newTop  + 'px';
  };

  const onUp = () => { dragging = false; };

  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup',   onUp);
}

function _onWordClick(e) {
  e.stopPropagation();
  e.preventDefault();

  const raw = e.target.textContent || '';
  // Strip leading/trailing punctuation for cleaner lookup
  const word = raw.replace(/^[\s.,!?;:'"()\[\]{}\-–—]+|[\s.,!?;:'"()\[\]{}\-–—]+$/g, '').trim();
  if (!word) return;

  console.log('[Lexora] Word clicked:', word);

  const video = document.querySelector('video');
  const wasPaused = video ? video.paused : true;
  if (video && !video.paused) video.pause();

  const timestamp = video ? Math.floor(video.currentTime) : 0;
  const lang = _getSubtitleLanguage();

  _showOverlay(word, wasPaused, timestamp, lang, video, null);

  // Client-side fallback: if the background script doesn't reply within 5s
  // (e.g. service worker sleeping, Odoo slow, fetch timed out) show the
  // "timed out" state so the Add-to-Vocabulary button appears.
  const _fallbackTimer = setTimeout(() => {
    console.warn('[Lexora] define response timeout — showing actions without definition');
    _showOverlay(word, wasPaused, timestamp, lang, video, { status: 'timeout', translations: [] });
  }, 5000);

  _sendMessage(
    { action: 'lexora-define', word, lang },
    (response) => {
      clearTimeout(_fallbackTimer);
      if (response && response.status === 'context_invalidated') {
        _showOverlay(word, wasPaused, timestamp, lang, video, { status: 'context_invalidated', translations: [] });
        return;
      }
      if (chrome.runtime.lastError) {
        console.warn('[Lexora] define lastError:', chrome.runtime.lastError.message);
        _showOverlay(word, wasPaused, timestamp, lang, video, { status: 'error', translations: [] });
        return;
      }
      console.log('[Lexora] define response received:', response);
      _showOverlay(word, wasPaused, timestamp, lang, video, response || { status: 'empty', translations: [] });
    }
  );
}

const _LANG_NAMES = { en: 'English', uk: 'Ukrainian', el: 'Greek' };

function _showOverlay(word, wasPaused, timestamp, lang, video, response) {
  _removeOverlay();
  _injectStyles();

  let bodyHtml;
  if (response === null) {
    // Loading state — waiting for background to reply
    bodyHtml = `<div class="lx-yt-loading">Looking up definition…</div>`;
  } else if (response && response.status === 'context_invalidated') {
    bodyHtml = `<div class="lx-yt-no-def">Lexora was updated — refresh this tab to restore subtitle features</div>`;
  } else if (response && response.status === 'unauthorized') {
    bodyHtml = `<div class="lx-yt-no-def">Sign in to Lexora to look up definitions</div>`;
  } else if (
    response && response.status === 'ok' &&
    response.translations && response.translations.length
  ) {
    const isLive = !!response.live;
    const rows = response.translations.map(t => `
      <div class="lx-yt-translation">
        <span class="lx-yt-lang-label">${_escHtml(_LANG_NAMES[t.target_language] || t.target_language)}</span>
        <span class="lx-yt-trans-text">${_escHtml(t.translated_text)}</span>
        ${isLive ? '<span class="lx-yt-live-badge">live</span>' : ''}
      </div>`).join('');
    bodyHtml = `<div class="lx-yt-translations">${rows}</div>`;
  } else if (response && (response.status === 'timeout' || response.status === 'error')) {
    bodyHtml = `
      <div class="lx-yt-no-def">Definition lookup timed out, but you can still save</div>
      <button class="lx-yt-retry-btn" id="lx-yt-retry">↺ Retry</button>`;
  } else {
    // ok-but-no-translations, empty — show neutral hint
    bodyHtml = `<div class="lx-yt-no-def">No definition yet — save to enrich</div>`;
  }

  // Show action buttons for every state except the initial loading spinner
  const showActions = response !== null;

  const overlay = document.createElement('div');
  overlay.id = _OVERLAY_ID;
  overlay.innerHTML = `
    <div class="lx-yt-card">
      <div class="lx-yt-card-header">
        <div class="lx-yt-logo">L</div>
        <span class="lx-yt-word">${_escHtml(word)}</span>
        <button class="lx-yt-close" id="lx-yt-close" title="Close">×</button>
      </div>
      <div class="lx-yt-body">
        <div class="lx-yt-scroll">
          ${bodyHtml}
          ${showActions ? `<div class="lx-yt-grammar-block" id="lx-yt-grammar"></div>` : ''}
        </div>
        ${showActions ? `
        <div class="lx-yt-footer">
          <div class="lx-yt-actions">
            <button class="lx-yt-add-btn" id="lx-yt-add">➕ Add to Vocabulary</button>
            <button class="lx-yt-resume-btn" id="lx-yt-resume">▶ Resume</button>
          </div>
          <button class="lx-yt-explain-btn" id="lx-yt-explain">Explain Grammar</button>
          <div class="lx-yt-status" id="lx-yt-status"></div>
        </div>` : ''}
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
  _makeDraggable(overlay);

  overlay.querySelector('#lx-yt-close')?.addEventListener('click', (e) => {
    e.stopPropagation();
    _removeOverlay();
    if (video && !wasPaused) video.play();
  });

  overlay.querySelector('#lx-yt-resume')?.addEventListener('click', (e) => {
    e.stopPropagation();
    _removeOverlay();
    if (video && !wasPaused) video.play();
  });

  overlay.querySelector('#lx-yt-retry')?.addEventListener('click', (e) => {
    e.stopPropagation();
    // Re-run the full lookup from scratch
    _removeOverlay();
    _showOverlay(word, wasPaused, timestamp, lang, video, null);
    const retryTimer = setTimeout(() => {
      _showOverlay(word, wasPaused, timestamp, lang, video, { status: 'timeout', translations: [] });
    }, 5000);
    _sendMessage(
      { action: 'lexora-define', word, lang },
      (response) => {
        clearTimeout(retryTimer);
        _showOverlay(word, wasPaused, timestamp, lang, video, response || { status: 'empty', translations: [] });
      }
    );
  });

  const explainBtn   = overlay.querySelector('#lx-yt-explain');
  const grammarBlock = overlay.querySelector('#lx-yt-grammar');
  if (explainBtn && grammarBlock) {
    explainBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      explainBtn.disabled = true;
      explainBtn.textContent = 'Explaining…';
      const timer = setTimeout(() => {
        grammarBlock.textContent = 'LLM timed out — try again.';
        grammarBlock.classList.add('lx-visible');
        explainBtn.textContent = 'Explain Grammar';
        explainBtn.disabled = false;
      }, 65000);
      _sendMessage({ action: 'lexora-explain-grammar', phrase: word, language: lang }, (resp) => {
        clearTimeout(timer);
        grammarBlock.textContent = resp?.explanation || 'Could not generate explanation.';
        grammarBlock.classList.add('lx-visible');
        explainBtn.textContent = 'Explain Grammar';
        explainBtn.disabled = false;
        const scrollEl = overlay.querySelector('.lx-yt-scroll');
        if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
      });
    });
  }

  const addBtn = overlay.querySelector('#lx-yt-add');
  if (addBtn) {
    addBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      addBtn.disabled = true;
      const statusEl = overlay.querySelector('#lx-yt-status');
      if (statusEl) statusEl.textContent = 'Saving…';

      const sourceUrl =
        `${location.href.split('#')[0]}${timestamp ? '#t=' + timestamp : ''}`;

      _sendMessage(
        { action: 'lexora-add-word-overlay', word, source_language: lang, source_url: sourceUrl },
        (resp) => {
          if (!statusEl) return;
          if (resp && resp.status === 'context_invalidated') {
            statusEl.style.color = '#f87171';
            statusEl.textContent = 'Extension updated — please refresh the page';
            addBtn.disabled = false;
            return;
          }
          if (chrome.runtime.lastError || !resp) {
            statusEl.style.color = '#f87171';
            statusEl.textContent = 'Error — check connection';
            addBtn.disabled = false;
            return;
          }
          if (resp.status === 'ok') {
            statusEl.style.color = '#4ade80';
            statusEl.textContent = '✓ Saved to your vocabulary!';
            setTimeout(() => {
              _removeOverlay();
              if (video && !wasPaused) video.play();
            }, 1400);
          } else if (resp.status === 'duplicate') {
            statusEl.style.color = '#fbbf24';
            statusEl.textContent = 'Already in your vocabulary';
            addBtn.disabled = false;
          } else if (resp.status === 'unauthorized') {
            statusEl.style.color = '#f87171';
            statusEl.textContent = 'Not logged in — open the extension and sign in';
            addBtn.disabled = false;
          } else {
            statusEl.style.color = '#f87171';
            statusEl.textContent = resp.message || 'Error saving word';
            addBtn.disabled = false;
          }
        }
      );
    });
  }
}

// ── MutationObserver ───────────────────────────────────────────────────────

let _captionObserver = null;

function _getContainer() {
  for (const sel of _CONTAINER_SELECTORS) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  return null;
}

function _getPlayerAnchor() {
  for (const sel of _PLAYER_SELECTORS) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  return null;
}

function _attachCaptionObserver() {
  if (_captionObserver) {
    _captionObserver.disconnect();
    _captionObserver = null;
  }

  const container = _getContainer();
  if (container) {
    console.log('[Lexora] Subtitle container found:', container.className || container.tagName);
    _captionObserver = new MutationObserver(() => _processAllCaptionElements());
    _captionObserver.observe(container, { childList: true, subtree: true, characterData: true });
    _processAllCaptionElements();
    return true;
  }

  console.log('[Lexora] Subtitle container not found yet — will retry via docObserver');
  return false;
}

// Observe the player anchor (always present) for caption container appearance.
// Falls back to document.body when the player hasn't rendered yet.
const _docObserver = new MutationObserver(() => {
  if (_captionObserver) {
    // Container already attached — just re-wrap new text that appeared
    _processAllCaptionElements();
    return;
  }
  if (_getContainer()) {
    _attachCaptionObserver();
  }
});

// ── Close-overlay helpers ──────────────────────────────────────────────────

document.addEventListener('click', (e) => {
  const overlay = document.getElementById(_OVERLAY_ID);
  if (
    overlay &&
    !overlay.contains(e.target) &&
    !e.target.classList.contains(_WORD_CLASS)
  ) {
    _removeOverlay();
  }
}, true);

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') _removeOverlay();
}, true);

// ── Entry point ────────────────────────────────────────────────────────────

function _init() {
  console.log('[Lexora] overlay.js initialised on', location.href);
  _injectStyles();

  // YouTube SPA navigation event — fires between video navigations
  window.addEventListener('yt-navigate-finish', () => {
    console.log('[Lexora] yt-navigate-finish — reconnecting caption observer');
    if (_captionObserver) { _captionObserver.disconnect(); _captionObserver = null; }
    _removeOverlay();
    // Brief delay: player re-renders after navigation event
    setTimeout(() => {
      if (!_attachCaptionObserver()) {
        // Container not ready; docObserver will pick it up when it appears
      }
    }, 900);
  });

  // Observe the player element if available, otherwise document root
  const observeRoot = _getPlayerAnchor() || document.body || document.documentElement;
  console.log('[Lexora] Attaching docObserver to:', observeRoot.tagName, observeRoot.id || observeRoot.className.slice(0, 30));
  _docObserver.observe(observeRoot, { childList: true, subtree: true });

  _attachCaptionObserver();
}

if (location.hostname === 'www.youtube.com') {
  // Run immediately if DOM is ready, otherwise wait
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }
}
