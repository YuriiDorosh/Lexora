'use strict';

// ---------------------------------------------------------------------------
// M24 — YouTube Subtitle Overlay
//
// MutationObserver wraps each word in .ytp-caption-segment with a clickable
// span. On click: pauses the video, fetches a definition from Lexora via the
// background service worker, shows a glassmorphism overlay card next to the
// subtitle bar. "Add to Vocabulary" saves the word with a timestamp URL.
// ---------------------------------------------------------------------------

const _OVERLAY_ID = 'lx-yt-overlay';
const _WORD_CLASS = 'lx-sub-word';
const _STYLES_ID = 'lx-overlay-styles';

const _OVERLAY_CSS = `
  .${_WORD_CLASS} {
    cursor: pointer;
    border-radius: 3px;
    transition: background 0.15s;
    padding: 1px 0;
  }
  .${_WORD_CLASS}:hover {
    background: rgba(99, 102, 241, 0.45);
    outline: 1px solid rgba(99, 102, 241, 0.7);
  }

  #${_OVERLAY_ID} {
    position: fixed;
    bottom: 120px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999999;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    animation: lx-yt-fadein 0.25s ease;
  }

  @keyframes lx-yt-fadein {
    from { opacity: 0; transform: translateX(-50%) translateY(12px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0); }
  }

  .lx-yt-card {
    min-width: 280px;
    max-width: 380px;
    background: rgba(10, 15, 30, 0.92);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 16px;
    box-shadow:
      0 12px 40px rgba(0, 0, 0, 0.6),
      0 2px 8px rgba(0, 0, 0, 0.4),
      inset 0 1px 0 rgba(255, 255, 255, 0.08);
    overflow: hidden;
  }

  .lx-yt-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  }

  .lx-yt-logo {
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.5px;
  }

  .lx-yt-word {
    flex: 1;
    font-size: 15px;
    font-weight: 700;
    color: #e0e7ff;
    letter-spacing: 0.2px;
  }

  .lx-yt-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.45);
    font-size: 18px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 6px;
    line-height: 1;
    transition: color 0.15s, background 0.15s;
  }
  .lx-yt-close:hover { color: #fff; background: rgba(255,255,255,0.1); }

  .lx-yt-body {
    padding: 10px 14px 12px;
  }

  .lx-yt-loading {
    color: rgba(255, 255, 255, 0.45);
    font-size: 13px;
    text-align: center;
    padding: 8px 0;
  }

  .lx-yt-translations {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 10px;
  }

  .lx-yt-translation {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .lx-yt-lang-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    color: rgba(165, 180, 252, 0.8);
    letter-spacing: 0.5px;
    flex-shrink: 0;
    min-width: 58px;
  }

  .lx-yt-trans-text {
    font-size: 14px;
    font-weight: 500;
    color: #f0f4ff;
    line-height: 1.4;
  }

  .lx-yt-no-def {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.4);
    font-style: italic;
    padding: 4px 0 8px;
  }

  .lx-yt-actions {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  .lx-yt-add-btn {
    flex: 1;
    padding: 7px 12px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    border: none;
    border-radius: 9px;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s, transform 0.1s;
  }
  .lx-yt-add-btn:hover { opacity: 0.88; }
  .lx-yt-add-btn:active { transform: scale(0.97); }
  .lx-yt-add-btn:disabled { opacity: 0.4; cursor: default; }

  .lx-yt-resume-btn {
    padding: 7px 14px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 9px;
    color: rgba(255,255,255,0.75);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }
  .lx-yt-resume-btn:hover { background: rgba(255,255,255,0.14); }

  .lx-yt-status {
    margin-top: 7px;
    font-size: 11px;
    font-weight: 600;
    min-height: 16px;
    text-align: center;
    color: rgba(255,255,255,0.6);
  }
`;

function _injectStyles() {
  if (document.getElementById(_STYLES_ID)) return;
  const style = document.createElement('style');
  style.id = _STYLES_ID;
  style.textContent = _OVERLAY_CSS;
  (document.head || document.documentElement).appendChild(style);
}

function _escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Detect the language of the active subtitle track
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

// Tokenise and wrap a subtitle segment element
function _wrapSegment(el) {
  if (el.querySelector('.' + _WORD_CLASS)) return; // already wrapped
  const text = el.textContent;
  if (!text.trim()) return;

  const parts = text.split(/(\s+)/);
  const frag = document.createDocumentFragment();
  for (const part of parts) {
    if (!part) continue;
    if (/^\s+$/.test(part)) {
      frag.appendChild(document.createTextNode(part));
    } else {
      const span = document.createElement('span');
      span.className = _WORD_CLASS;
      span.textContent = part;
      span.addEventListener('click', _onWordClick);
      frag.appendChild(span);
    }
  }
  el.textContent = '';
  el.appendChild(frag);
}

function _removeOverlay() {
  document.getElementById(_OVERLAY_ID)?.remove();
}

// Handle word click: pause video, show loading overlay, fetch definition
function _onWordClick(e) {
  e.stopPropagation();

  // Strip leading/trailing punctuation for clean lookup
  const raw = e.target.textContent || '';
  const word = raw.replace(/^[.,!?;:'"()\[\]{}\-–—]+|[.,!?;:'"()\[\]{}\-–—]+$/g, '').trim();
  if (!word) return;

  const video = document.querySelector('video');
  const wasPaused = video ? video.paused : true;
  if (video && !video.paused) video.pause();

  const timestamp = video ? Math.floor(video.currentTime) : 0;
  const lang = _getSubtitleLanguage();

  _showOverlay(word, wasPaused, timestamp, lang, video, null);

  chrome.runtime.sendMessage(
    { action: 'lexora-define', word, lang },
    (response) => {
      if (chrome.runtime.lastError) {
        _showOverlay(word, wasPaused, timestamp, lang, video, { status: 'error' });
      } else {
        _showOverlay(word, wasPaused, timestamp, lang, video, response);
      }
    }
  );
}

const _LANG_NAMES = { en: 'English', uk: 'Ukrainian', el: 'Greek' };

function _showOverlay(word, wasPaused, timestamp, lang, video, response) {
  _removeOverlay();
  _injectStyles();

  let bodyHtml;
  if (response === null) {
    // Loading state
    bodyHtml = `<div class="lx-yt-loading">Looking up definition…</div>`;
  } else if (response && response.status === 'ok' && response.translations && response.translations.length) {
    const rows = response.translations.map(t => `
      <div class="lx-yt-translation">
        <span class="lx-yt-lang-label">${_escHtml(_LANG_NAMES[t.target_language] || t.target_language)}</span>
        <span class="lx-yt-trans-text">${_escHtml(t.translated_text)}</span>
      </div>`).join('');
    bodyHtml = `<div class="lx-yt-translations">${rows}</div>`;
  } else {
    bodyHtml = `<div class="lx-yt-no-def">No definition yet — save to enrich</div>`;
  }

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
        ${bodyHtml}
        ${response !== null ? `
        <div class="lx-yt-actions">
          <button class="lx-yt-add-btn" id="lx-yt-add">➕ Add to Vocabulary</button>
          <button class="lx-yt-resume-btn" id="lx-yt-resume">▶ Resume</button>
        </div>
        <div class="lx-yt-status" id="lx-yt-status"></div>` : ''}
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  overlay.querySelector('#lx-yt-close')?.addEventListener('click', () => {
    _removeOverlay();
    if (video && !wasPaused) video.play();
  });

  overlay.querySelector('#lx-yt-resume')?.addEventListener('click', () => {
    _removeOverlay();
    if (video && !wasPaused) video.play();
  });

  const addBtn = overlay.querySelector('#lx-yt-add');
  if (addBtn) {
    addBtn.addEventListener('click', () => {
      addBtn.disabled = true;
      const statusEl = overlay.querySelector('#lx-yt-status');
      if (statusEl) statusEl.textContent = 'Saving…';

      const sourceUrl = `${location.href.split('#')[0]}${timestamp ? '#t=' + timestamp : ''}`;
      chrome.runtime.sendMessage(
        { action: 'lexora-add-word-overlay', word, source_language: lang, source_url: sourceUrl },
        (resp) => {
          if (!statusEl) return;
          if (chrome.runtime.lastError || !resp) {
            statusEl.style.color = '#f87171';
            statusEl.textContent = 'Error — check connection';
            addBtn.disabled = false;
            return;
          }
          if (resp.status === 'ok') {
            statusEl.style.color = '#4ade80';
            statusEl.textContent = '✓ Saved to your vocabulary!';
            setTimeout(() => { _removeOverlay(); if (video && !wasPaused) video.play(); }, 1400);
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

// ── YouTube subtitle observer ──────────────────────────────────────────────

function _processSegments() {
  document.querySelectorAll('.ytp-caption-segment').forEach(_wrapSegment);
}

let _captionObserver = null;

function _attachCaptionObserver() {
  const container = document.querySelector('.ytp-caption-window-container');
  if (!container || _captionObserver) return;

  _captionObserver = new MutationObserver(() => _processSegments());
  _captionObserver.observe(container, { childList: true, subtree: true });
  _processSegments();
}

// YouTube is a SPA — caption container may not exist on load
const _bodyObserver = new MutationObserver(() => {
  if (document.querySelector('.ytp-caption-window-container')) {
    _attachCaptionObserver();
    // keep observing — navigating to a new video recreates the container
  }
});

// Close overlay when clicking outside
document.addEventListener('click', (e) => {
  const overlay = document.getElementById(_OVERLAY_ID);
  if (overlay && !overlay.contains(e.target) && !e.target.classList.contains(_WORD_CLASS)) {
    _removeOverlay();
  }
}, true);

// Keyboard dismiss
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') _removeOverlay();
}, true);

if (location.hostname === 'www.youtube.com') {
  _bodyObserver.observe(document.body, { childList: true, subtree: true });
  _attachCaptionObserver();
}
