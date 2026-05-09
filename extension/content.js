'use strict';

// ---------------------------------------------------------------------------
// Lexora content script — M23 Contextual Capture + Toast Notifications
// ---------------------------------------------------------------------------

// ── Sentence extraction ────────────────────────────────────────────────────

function getSurroundingSentence(selectedText) {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return '';

  const range = sel.getRangeAt(0);
  const container = range.startContainer;

  let node = container.nodeType === Node.TEXT_NODE ? container : container.firstChild;
  let fullText = '';

  if (node && node.parentElement) {
    let block = node.parentElement;
    while (block && !isBlockElement(block)) block = block.parentElement;
    fullText = block ? (block.textContent || '') : (node.parentElement.textContent || '');
  }

  if (!fullText) return '';

  const sentences = fullText.split(/(?<=[.!?])\s+/);
  const lower = selectedText.toLowerCase();
  for (const s of sentences) {
    if (s.toLowerCase().includes(lower)) {
      const trimmed = s.trim();
      if (trimmed.length <= 500) return trimmed;
      const idx = trimmed.toLowerCase().indexOf(lower);
      const start = Math.max(0, idx - 100);
      const end = Math.min(trimmed.length, idx + lower.length + 200);
      return trimmed.slice(start, end).trim();
    }
  }
  return '';
}

function isBlockElement(el) {
  const blocks = new Set(['P','DIV','LI','TD','TH','H1','H2','H3','H4','H5','H6',
    'BLOCKQUOTE','ARTICLE','SECTION','MAIN','ASIDE','FIGCAPTION','CAPTION']);
  return blocks.has(el.tagName);
}

function captureSelection() {
  const word = window.getSelection()?.toString().trim() || '';
  if (!word) return { word: '', context_sentence: '' };
  return { word, context_sentence: getSurroundingSentence(word) };
}

window.__lexoraCaptureSelection = captureSelection;

// ── Premium Toast Notification ─────────────────────────────────────────────

const TOAST_STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

  #lexora-toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 999999;
    display: flex;
    flex-direction: column;
    gap: 10px;
    pointer-events: none;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  .lexora-toast {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    min-width: 300px;
    max-width: 380px;
    padding: 14px 16px;
    border-radius: 14px;
    background: rgba(15, 23, 42, 0.85);
    backdrop-filter: blur(16px) saturate(180%);
    -webkit-backdrop-filter: blur(16px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.4),
      0 2px 8px rgba(0, 0, 0, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.08);
    pointer-events: auto;
    transform: translateX(120%);
    opacity: 0;
    transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1),
                opacity 0.35s ease;
    will-change: transform, opacity;
  }

  .lexora-toast.lx-toast-show {
    transform: translateX(0);
    opacity: 1;
  }

  .lexora-toast.lx-toast-hide {
    transform: translateX(120%);
    opacity: 0;
    transition: transform 0.3s ease-in, opacity 0.3s ease-in;
  }

  .lexora-toast-logo {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    font-weight: 800;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: #fff;
    letter-spacing: -0.5px;
  }

  .lexora-toast-body {
    flex: 1;
    min-width: 0;
  }

  .lexora-toast-title {
    font-size: 13px;
    font-weight: 600;
    line-height: 1.4;
    margin-bottom: 2px;
  }

  .lexora-toast-title .lx-word-highlight {
    color: #a5b4fc;
  }

  .lexora-toast-sub {
    font-size: 11px;
    font-weight: 400;
    line-height: 1.4;
    opacity: 0.6;
  }

  .lexora-toast.lx-ok   .lexora-toast-title { color: #d1fae5; }
  .lexora-toast.lx-ok   { border-color: rgba(52, 211, 153, 0.25); }

  .lexora-toast.lx-dup  .lexora-toast-title { color: #fef3c7; }
  .lexora-toast.lx-dup  { border-color: rgba(251, 191, 36, 0.25); }

  .lexora-toast.lx-err  .lexora-toast-title { color: #fee2e2; }
  .lexora-toast.lx-err  { border-color: rgba(248, 113, 113, 0.25); }

  .lexora-toast-progress {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 2px;
    border-radius: 0 0 14px 14px;
    width: 100%;
    transform-origin: left;
    animation: lx-progress 3.5s linear forwards;
  }

  .lexora-toast { position: relative; overflow: hidden; }

  .lx-ok  .lexora-toast-progress { background: linear-gradient(90deg, #34d399, #059669); }
  .lx-dup .lexora-toast-progress { background: linear-gradient(90deg, #fbbf24, #d97706); }
  .lx-err .lexora-toast-progress { background: linear-gradient(90deg, #f87171, #dc2626); }

  @keyframes lx-progress {
    from { transform: scaleX(1); }
    to   { transform: scaleX(0); }
  }
`;

function ensureToastStyles() {
  if (document.getElementById('lexora-toast-styles')) return;
  const style = document.createElement('style');
  style.id = 'lexora-toast-styles';
  style.textContent = TOAST_STYLES;
  document.head.appendChild(style);
}

function ensureToastContainer() {
  let container = document.getElementById('lexora-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'lexora-toast-container';
    document.body.appendChild(container);
  }
  return container;
}

function showLexoraToast(status, word) {
  ensureToastStyles();
  const container = ensureToastContainer();

  const CONFIG = {
    ok:  { cls: 'lx-ok',  icon: '✓', title: `<span class="lx-word-highlight">${escHtml(word)}</span> added to your vocabulary!`, sub: 'Translation will be queued automatically.' },
    duplicate: { cls: 'lx-dup', icon: '≡', title: `<span class="lx-word-highlight">${escHtml(word)}</span> is already in your list.`, sub: 'No duplicate was created.' },
    error: { cls: 'lx-err', icon: '!', title: `Couldn't save <span class="lx-word-highlight">${escHtml(word)}</span>.`, sub: 'Check your connection or log in to Lexora.' },
    unauthorized: { cls: 'lx-err', icon: '!', title: 'Not logged in to Lexora.', sub: 'Open the extension and sign in first.' },
  };

  const cfg = CONFIG[status] || CONFIG.error;

  const toast = document.createElement('div');
  toast.className = `lexora-toast ${cfg.cls}`;
  toast.innerHTML = `
    <div class="lexora-toast-logo">L</div>
    <div class="lexora-toast-body">
      <div class="lexora-toast-title">${cfg.title}</div>
      <div class="lexora-toast-sub">${cfg.sub}</div>
    </div>
    <div class="lexora-toast-progress"></div>
  `;

  container.appendChild(toast);

  // Trigger slide-in on next frame
  requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add('lx-toast-show')));

  // Slide-out after 3.5 s
  setTimeout(() => {
    toast.classList.add('lx-toast-hide');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
  }, 3500);
}

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Message listener ───────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.action === 'show-toast') {
    showLexoraToast(msg.status, msg.word || '');
  }
});

// ── Quick Look Overlay — text selection on any page ────────────────────────
// Shows a floating "L" icon when text is selected; clicking it opens a
// glassmorphism card with a live translation + Add-to-Vocabulary button.
// Rendered inside a Shadow DOM so page styles cannot bleed in.

const _QL_HOST_ID  = 'lx-ql-shadow-host';
const _QL_ICON_ID  = 'lx-ql-icon';
const _QL_MIN_LEN  = 2;
const _QL_MAX_LEN  = 1000;

const _QL_LANG_NAMES = { en: 'EN', uk: 'UK', el: 'EL', pl: 'PL' };

// Shadow DOM stylesheet — isolated from the host page
const _QL_CSS = `
  * { box-sizing: border-box; margin: 0; padding: 0; }

  .lx-ql-card {
    position: absolute;
    width: 300px;
    max-width: calc(100vw - 24px);
    max-height: 80vh !important;
    display: flex !important;
    flex-direction: column !important;
    background: rgba(10, 14, 28, 0.93);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255,255,255,0.11);
    border-radius: 16px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 2px 12px rgba(0,0,0,0.4),
                inset 0 1px 0 rgba(255,255,255,0.07);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    color: #e2e8f0;
    overflow: hidden !important;
    pointer-events: all;
    animation: lx-ql-pop 0.18s cubic-bezier(0.34,1.56,0.64,1) both;
  }

  @keyframes lx-ql-pop {
    from { opacity: 0; transform: translateY(6px) scale(0.96); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }

  .lx-ql-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 14px 8px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    cursor: move;
    user-select: none;
  }

  .lx-ql-logo {
    flex-shrink: 0;
    width: 24px; height: 24px;
    border-radius: 7px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 800; letter-spacing: -0.3px;
  }

  .lx-ql-word {
    flex: 1;
    font-size: 14px; font-weight: 700; color: #f1f5f9;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; word-break: break-word;
  }

  .lx-ql-close {
    all: unset;
    color: rgba(255,255,255,0.35);
    font-size: 20px; line-height: 1;
    cursor: pointer; padding: 0 2px; border-radius: 4px;
    transition: color 0.15s;
  }
  .lx-ql-close:hover { color: #fff; }

  .lx-ql-body {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto !important;
    overflow: hidden !important;
    min-height: 0 !important;
    padding: 0;
  }

  .lx-ql-scroll {
    overflow-y: auto !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    padding: 10px 14px 6px;
    scrollbar-width: thin; scrollbar-color: rgba(99,102,241,0.4) transparent;
  }
  .lx-ql-scroll::-webkit-scrollbar { width: 4px; }
  .lx-ql-scroll::-webkit-scrollbar-track { background: transparent; }
  .lx-ql-scroll::-webkit-scrollbar-thumb {
    background: rgba(99,102,241,0.4); border-radius: 4px;
  }

  .lx-ql-footer {
    padding: 4px 14px 12px;
    border-top: 1px solid rgba(255,255,255,0.06);
    flex-shrink: 0 !important;
  }

  .lx-ql-loading, .lx-ql-no-def {
    font-size: 12px; color: rgba(255,255,255,0.42);
    text-align: center; padding: 6px 0 8px;
  }

  .lx-ql-translations { margin-bottom: 6px; }

  .lx-ql-translation {
    display: flex; align-items: baseline; gap: 8px; padding: 4px 0;
  }

  .lx-ql-lang-label {
    font-size: 10px; font-weight: 700;
    color: rgba(99,102,241,0.9);
    text-transform: uppercase; letter-spacing: 0.5px;
    flex-shrink: 0; min-width: 26px;
  }

  .lx-ql-trans-text {
    font-size: 13px; font-weight: 600; color: #e2e8f0;
  }

  .lx-ql-live-badge {
    font-size: 9px; font-weight: 700;
    background: rgba(99,102,241,0.18);
    border: 1px solid rgba(99,102,241,0.32);
    color: #a5b4fc; border-radius: 4px;
    padding: 1px 4px; margin-left: 4px;
    vertical-align: middle; letter-spacing: 0.3px;
  }

  .lx-ql-actions { display: flex; gap: 6px; margin-top: 0; }

  .lx-ql-add-btn {
    all: unset;
    flex: 1; text-align: center;
    padding: 8px 12px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    border-radius: 9px;
    color: #fff; font-size: 12px; font-weight: 700;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  .lx-ql-add-btn:hover { opacity: 0.88; }
  .lx-ql-add-btn:disabled { opacity: 0.4; cursor: default; }

  .lx-ql-retry-btn {
    all: unset;
    padding: 8px 12px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 9px;
    color: rgba(255,255,255,0.7); font-size: 12px; font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }
  .lx-ql-retry-btn:hover { background: rgba(255,255,255,0.1); }

  .lx-ql-status {
    margin-top: 6px; font-size: 11px; font-weight: 600;
    min-height: 14px; color: rgba(255,255,255,0.5); text-align: center;
  }

  .lx-ql-explain-btn {
    margin-top: 6px; width: 100%; padding: 6px 0;
    background: rgba(139,92,246,0.15);
    border: 1px solid rgba(139,92,246,0.4);
    border-radius: 8px; color: #c4b5fd; font-size: 12px; font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
    pointer-events: auto;
  }
  .lx-ql-explain-btn:hover { background: rgba(139,92,246,0.3); }
  .lx-ql-explain-btn:disabled { opacity: 0.5; cursor: default; }

  .lx-ql-grammar-block {
    display: none; margin-top: 8px; padding: 10px 12px;
    background: rgba(139,92,246,0.08);
    border-left: 3px solid #7c3aed;
    border-radius: 0 8px 8px 0;
    font-size: 12px; line-height: 1.6; color: #ddd6fe;
  }
  .lx-ql-grammar-block.lx-visible { display: block; }

  /* M32 — Slang/Idiom Explainer (sibling of grammar block, amber accent) */
  .lx-ql-slang-btn {
    margin-top: 6px; width: 100%; padding: 6px 0;
    background: rgba(245,158,11,0.15);
    border: 1px solid rgba(245,158,11,0.4);
    border-radius: 8px; color: #fde68a; font-size: 12px; font-weight: 600;
    cursor: pointer; transition: background 0.15s;
    pointer-events: auto;
  }
  .lx-ql-slang-btn:hover { background: rgba(245,158,11,0.3); }
  .lx-ql-slang-btn:disabled { opacity: 0.5; cursor: default; }

  .lx-ql-slang-block {
    display: none; margin-top: 8px; padding: 10px 12px;
    background: rgba(245,158,11,0.08);
    border-left: 3px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    font-size: 12px; line-height: 1.6; color: #fef3c7;
  }
  .lx-ql-slang-block.lx-visible { display: block; }
  .lx-ql-slang-kind {
    display: inline-block; margin-bottom: 6px;
    padding: 1px 8px; border-radius: 999px;
    background: rgba(245,158,11,0.25); color: #fbbf24;
    font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .lx-ql-slang-figurative {
    margin: 4px 0 6px;
    font-size: 13px; font-weight: 600; color: #fef3c7;
  }
  .lx-ql-slang-literal {
    margin-bottom: 6px;
    font-size: 11px; font-style: italic; color: #fde68a; opacity: 0.85;
  }
  .lx-ql-slang-example {
    margin-top: 6px; padding: 6px 10px;
    background: rgba(255,255,255,0.04);
    border-radius: 6px;
    font-size: 11px; font-style: italic; color: #fef3c7;
  }
  .lx-ql-slang-uncertain {
    display: block; margin-top: 6px;
    font-size: 11px; font-style: italic; color: #f87171;
  }
`;

// ── helpers ────────────────────────────────────────────────────────────────

function _detectLang(text) {
  if (/[Ѐ-ӿ]/.test(text)) return 'uk';
  if (/[Ͱ-Ͽἀ-῿]/.test(text)) return 'el';
  if (/[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/.test(text)) return 'pl';
  return 'en';
}

function _qlSendMessage(msg, callback) {
  try {
    if (typeof chrome === 'undefined' || !chrome.runtime?.id) {
      console.warn('[Lexora QL] extension context invalid — cannot send message');
      callback?.({ status: 'context_invalidated' });
      return;
    }
    console.log('[Lexora QL] sending message to background:', msg.action, '| word:', msg.word);
    chrome.runtime.sendMessage(msg, (response) => {
      // MUST check lastError here; if the SW didn't respond, response is undefined
      // and lastError is set. Ignoring it causes Chrome to log "Unchecked lastError".
      if (chrome.runtime.lastError) {
        console.error('[Lexora QL] sendMessage lastError:', chrome.runtime.lastError.message);
        callback?.({ status: 'error', message: chrome.runtime.lastError.message });
        return;
      }
      callback?.(response);
    });
  } catch (err) {
    console.error('[Lexora QL] sendMessage threw:', err.message);
    callback?.({ status: 'error', message: err.message });
  }
}

function _removeQlIcon() {
  document.getElementById(_QL_ICON_ID)?.remove();
}

function _removeQlOverlay() {
  document.getElementById(_QL_HOST_ID)?.remove();
}

// ── icon ───────────────────────────────────────────────────────────────────

function _showQlIcon(word, rect) {
  _removeQlIcon();

  const icon = document.createElement('button');
  icon.id = _QL_ICON_ID;

  // Viewport-safe position: right edge of selection, vertically centred
  const iconSize = 28;
  let left = rect.right + 8;
  let top  = rect.top + (rect.height / 2) - (iconSize / 2);
  if (left + iconSize > window.innerWidth - 8) left = rect.left - iconSize - 8;
  if (top < 4) top = 4;
  if (top + iconSize > window.innerHeight - 4) top = window.innerHeight - iconSize - 4;

  Object.assign(icon.style, {
    all: 'initial',
    position: 'fixed',
    left: `${Math.round(left)}px`,
    top:  `${Math.round(top)}px`,
    width: `${iconSize}px`, height: `${iconSize}px`,
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
    boxShadow: '0 2px 10px rgba(79,70,229,0.55)',
    color: '#fff',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: '13px', fontWeight: '800',
    cursor: 'pointer',
    zIndex: '2147483647',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    userSelect: 'none',
    border: 'none', outline: 'none',
    transition: 'transform 0.12s ease, box-shadow 0.12s ease',
    pointerEvents: 'all',
  });
  icon.textContent = 'L';
  icon.title = 'Lexora Quick Look';

  icon.addEventListener('mouseenter', () => {
    icon.style.transform = 'scale(1.18)';
    icon.style.boxShadow = '0 4px 16px rgba(79,70,229,0.7)';
  });
  icon.addEventListener('mouseleave', () => {
    icon.style.transform = 'scale(1)';
    icon.style.boxShadow = '0 2px 10px rgba(79,70,229,0.55)';
  });
  icon.addEventListener('mousedown', (e) => {
    e.preventDefault();
    e.stopPropagation();
    _removeQlIcon();
    _openQlOverlay(word, rect);
  });

  document.body.appendChild(icon);
}

// ── overlay ────────────────────────────────────────────────────────────────

function _renderQlOverlay(word, anchorRect, response) {
  console.log('[Lexora QL] renderQlOverlay — word:', word, '| status:', response?.status, '| translations:', response?.translations?.length ?? 'n/a');
  _removeQlOverlay();

  const host = document.createElement('div');
  host.id = _QL_HOST_ID;
  Object.assign(host.style, {
    position: 'fixed',
    inset: '0',
    width: '0',
    height: '0',
    overflow: 'visible',
    pointerEvents: 'none',
    zIndex: '2147483647',
  });

  const shadow = host.attachShadow({ mode: 'open' });

  // Card position: below selection, viewport-clamped
  const cardW = 300;
  let left = Math.round(Math.min(anchorRect.left, window.innerWidth - cardW - 12));
  left = Math.max(8, left);
  let top = Math.round(anchorRect.bottom + 8);
  if (top + 220 > window.innerHeight - 8) top = Math.max(8, Math.round(anchorRect.top - 230));

  // Body HTML
  let bodyHtml;
  const isLive = response?.live;

  if (!response) {
    bodyHtml = `<div class="lx-ql-loading">Looking up translation…</div>`;
  } else if (response.status === 'unauthorized') {
    bodyHtml = `<div class="lx-ql-no-def">Sign in to Lexora to look up words</div>`;
  } else if (response.status === 'context_invalidated') {
    bodyHtml = `<div class="lx-ql-no-def">Refresh this tab to restore Lexora</div>`;
  } else if (response.status === 'timeout' || response.status === 'error') {
    const errDetail = response.message ? ` (${response.message})` : '';
    bodyHtml = `
      <div class="lx-ql-no-def">Lookup failed${errDetail} — you can still save it</div>
      <button class="lx-ql-retry-btn" id="lx-ql-retry">↺ Retry</button>`;
  } else if (response.translations?.length) {
    const rows = response.translations.map(t => `
      <div class="lx-ql-translation">
        <span class="lx-ql-lang-label">${_QL_LANG_NAMES[t.target_language] || t.target_language}</span>
        <span class="lx-ql-trans-text">${escHtml(t.translated_text)}</span>
        ${isLive ? '<span class="lx-ql-live-badge">live</span>' : ''}
      </div>`).join('');
    bodyHtml = `<div class="lx-ql-translations">${rows}</div>`;
  } else {
    bodyHtml = `<div class="lx-ql-no-def">No translation yet — save to enrich</div>`;
  }

  const showActions = response !== null;

  shadow.innerHTML = `
    <style>${_QL_CSS}</style>
    <div class="lx-ql-card" style="left:${left}px;top:${top}px;">
      <div class="lx-ql-header">
        <div class="lx-ql-logo">L</div>
        <span class="lx-ql-word">${escHtml(word)}</span>
        <button class="lx-ql-close" id="lx-ql-close" title="Close">×</button>
      </div>
      <div class="lx-ql-body">
        <div class="lx-ql-scroll">
          ${bodyHtml}
          ${showActions ? `<div class="lx-ql-grammar-block" id="lx-ql-grammar"></div>` : ''}
          ${showActions ? `<div class="lx-ql-slang-block"   id="lx-ql-slang"></div>`   : ''}
        </div>
        ${showActions ? `
          <div class="lx-ql-footer">
            <div class="lx-ql-actions">
              <button class="lx-ql-add-btn" id="lx-ql-add">➕ Add to Vocabulary</button>
            </div>
            <button class="lx-ql-explain-btn" id="lx-ql-explain">Explain Grammar</button>
            <button class="lx-ql-slang-btn"   id="lx-ql-explain-slang">💡 Explain Slang/Idiom</button>
            <div class="lx-ql-status" id="lx-ql-status"></div>
          </div>
        ` : ''}
      </div>
    </div>
  `;

  document.body.appendChild(host);
  _makeQlDraggable(shadow);

  shadow.getElementById('lx-ql-close')?.addEventListener('click', (e) => {
    e.stopPropagation();
    _removeQlOverlay();
  });

  shadow.getElementById('lx-ql-retry')?.addEventListener('click', (e) => {
    e.stopPropagation();
    _renderQlOverlay(word, anchorRect, null);
    const timer = setTimeout(() => {
      _renderQlOverlay(word, anchorRect, { status: 'timeout', translations: [] });
    }, 5000);
    _qlSendMessage({ action: 'lexora-define', word, lang: _detectLang(word) }, (resp) => {
      clearTimeout(timer);
      _renderQlOverlay(word, anchorRect, resp || { status: 'empty', translations: [] });
    });
  });

  const explainBtn   = shadow.getElementById('lx-ql-explain');
  const grammarBlock = shadow.getElementById('lx-ql-grammar');
  if (explainBtn && grammarBlock) {
    explainBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      explainBtn.disabled = true;
      explainBtn.textContent = 'Explaining…';
      const lang = _detectLang(word);
      const timer = setTimeout(() => {
        grammarBlock.textContent = 'LLM timed out — try again.';
        grammarBlock.classList.add('lx-visible');
        explainBtn.textContent = 'Explain Grammar';
        explainBtn.disabled = false;
      }, 65000);
      _qlSendMessage({ action: 'lexora-explain-grammar', phrase: word, language: lang }, (resp) => {
        clearTimeout(timer);
        grammarBlock.textContent = resp?.explanation || 'Could not generate explanation.';
        grammarBlock.classList.add('lx-visible');
        explainBtn.textContent = 'Explain Grammar';
        explainBtn.disabled = false;
        const scrollEl = shadow.querySelector('.lx-ql-scroll');
        if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
      });
    });
  }

  // M32 — Explain Slang/Idiom button
  const slangBtn   = shadow.getElementById('lx-ql-explain-slang');
  const slangBlock = shadow.getElementById('lx-ql-slang');
  if (slangBtn && slangBlock) {
    slangBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      slangBtn.disabled = true;
      const originalLabel = slangBtn.textContent;
      slangBtn.textContent = 'Looking up…';

      const sourceLang = _detectLang(word);
      const timer = setTimeout(() => {
        slangBlock.innerHTML = '<em>LLM timed out — try again.</em>';
        slangBlock.classList.add('lx-visible');
        slangBtn.textContent = originalLabel;
        slangBtn.disabled = false;
      }, 65000);

      // Read user's chosen explanation language; default 'en' until the
      // Options dropdown is populated.
      chrome.storage.sync.get('lexora_native_language', (cfg) => {
        const nativeLang = (cfg && cfg.lexora_native_language) || 'en';
        _qlSendMessage({
          action: 'lexora-explain-slang',
          phrase: word,
          source_language: sourceLang,
          native_language: nativeLang,
        }, (resp) => {
          clearTimeout(timer);
          _renderSlangBlock(slangBlock, resp);
          slangBtn.textContent = originalLabel;
          slangBtn.disabled = false;
          const scrollEl = shadow.querySelector('.lx-ql-scroll');
          if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
        });
      });
    });
  }

  const addBtn   = shadow.getElementById('lx-ql-add');
  const statusEl = shadow.getElementById('lx-ql-status');
  if (addBtn) {
    addBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      addBtn.disabled = true;
      if (statusEl) statusEl.textContent = 'Saving…';
      _qlSendMessage(
        { action: 'lexora-add-word-overlay', word, source_language: _detectLang(word), source_url: location.href },
        (resp) => {
          if (!statusEl) return;
          if (!resp || resp.status === 'error' || resp.status === 'context_invalidated') {
            statusEl.style.color = '#f87171';
            statusEl.textContent = 'Error — check connection or sign in';
            addBtn.disabled = false;
          } else if (resp.status === 'duplicate') {
            statusEl.style.color = '#fbbf24';
            statusEl.textContent = 'Already in your vocabulary';
          } else {
            statusEl.style.color = '#4ade80';
            statusEl.textContent = '✓ Saved!';
            setTimeout(() => _removeQlOverlay(), 1500);
          }
        }
      );
    });
  }
}

// ── M32 — Slang/Idiom render helper (shared shape across QL + YouTube) ────

const _SLANG_KIND_LABELS = {
  idiom: 'Idiom', slang: 'Slang', phrasal_verb: 'Phrasal Verb',
  literal: 'Literal', unknown: 'Unknown',
};

// Build the inner HTML for a slang block. Caller decides which container
// element to drop it into (Quick Look or YouTube overlay) — the shape and
// CSS class names are shared between both surfaces.
function _renderSlangBlock(container, resp) {
  if (!container) return;
  if (!resp) {
    container.innerHTML = '<em>No response from background.</em>';
    container.classList.add('lx-visible');
    return;
  }
  if (resp.status === 'context_invalidated') {
    container.innerHTML = '<em>Refresh this tab to restore Lexora.</em>';
    container.classList.add('lx-visible');
    return;
  }
  if (resp.status === 'unauthorized') {
    container.innerHTML = '<em>Please sign in to Lexora first.</em>';
    container.classList.add('lx-visible');
    return;
  }
  if (resp.status === 'unavailable') {
    container.innerHTML = `<em>${escHtml(resp.message || 'LLM unavailable.')}</em>`;
    container.classList.add('lx-visible');
    return;
  }
  if (resp.status === 'error') {
    container.innerHTML = `<em>${escHtml(resp.message || 'Could not look up phrase.')}</em>`;
    container.classList.add('lx-visible');
    return;
  }

  const kind = (resp.kind || 'unknown').toLowerCase();
  const figurative = (resp.figurative_meaning || '').trim();
  const literal    = (resp.literal_meaning    || '').trim();
  const example    = (resp.example            || '').trim();
  const confidence = (resp.confidence || 'low').toLowerCase();
  const kindLabel  = _SLANG_KIND_LABELS[kind] || _SLANG_KIND_LABELS.unknown;

  // Special branch: literal phrases get a "this is literal" notice rather
  // than a fake figurative explanation, so users aren't misled.
  if (kind === 'literal') {
    let html = `<span class="lx-ql-slang-kind">${escHtml(kindLabel)}</span>`;
    html += `<div class="lx-ql-slang-figurative">This phrase translates literally — no figurative meaning.</div>`;
    if (literal) html += `<div class="lx-ql-slang-literal">${escHtml(literal)}</div>`;
    container.innerHTML = html;
    container.classList.add('lx-visible');
    return;
  }

  let html = `<span class="lx-ql-slang-kind">${escHtml(kindLabel)}</span>`;
  if (figurative) html += `<div class="lx-ql-slang-figurative">${escHtml(figurative)}</div>`;
  if (literal && literal !== figurative) {
    html += `<div class="lx-ql-slang-literal">Literally: ${escHtml(literal)}</div>`;
  }
  if (example) {
    html += `<div class="lx-ql-slang-example">"${escHtml(example)}"</div>`;
  }
  if (confidence === 'low') {
    html += `<em class="lx-ql-slang-uncertain">⚠ AI is uncertain — consider checking a dictionary.</em>`;
  }
  if (!figurative && !literal && !example) {
    html += `<em>Could not classify this phrase.</em>`;
  }
  container.innerHTML = html;
  container.classList.add('lx-visible');
}

// ── draggable card (Quick Look) ────────────────────────────────────────────

function _makeQlDraggable(shadow) {
  const card   = shadow.querySelector('.lx-ql-card');
  const handle = shadow.querySelector('.lx-ql-header');
  if (!card || !handle) return;

  let dragging = false, startX = 0, startY = 0, originLeft = 0, originTop = 0;

  handle.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    dragging   = true;
    startX     = e.clientX;
    startY     = e.clientY;
    originLeft = parseInt(card.style.left, 10) || 0;
    originTop  = parseInt(card.style.top,  10) || 0;
    e.preventDefault();
    e.stopPropagation();
  });

  const onMove = (e) => {
    if (!dragging) return;
    const newLeft = Math.max(0, Math.min(window.innerWidth  - card.offsetWidth,  originLeft + e.clientX - startX));
    const newTop  = Math.max(0, Math.min(window.innerHeight - card.offsetHeight, originTop  + e.clientY - startY));
    card.style.left = newLeft + 'px';
    card.style.top  = newTop  + 'px';
  };

  const onUp = () => { dragging = false; };

  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup',   onUp);
}

function _openQlOverlay(word, anchorRect) {
  _renderQlOverlay(word, anchorRect, null);

  const lang = _detectLang(word);
  const timer = setTimeout(() => {
    _renderQlOverlay(word, anchorRect, { status: 'timeout', translations: [] });
  }, 5000);

  _qlSendMessage({ action: 'lexora-define', word, lang }, (response) => {
    clearTimeout(timer);
    _renderQlOverlay(word, anchorRect, response || { status: 'empty', translations: [] });
  });
}

// ── Selection listener ─────────────────────────────────────────────────────

let _qlSelTimer = null;

document.addEventListener('mouseup', (e) => {
  // Ignore clicks inside our own UI
  if (e.target?.id === _QL_ICON_ID) return;
  if (e.target?.closest?.(`#${_QL_HOST_ID}`)) return;

  clearTimeout(_qlSelTimer);
  _qlSelTimer = setTimeout(() => {
    const sel  = window.getSelection();
    const text = sel?.toString().trim() || '';

    if (text.length < _QL_MIN_LEN || text.length > _QL_MAX_LEN) {
      _removeQlIcon();
      return;
    }

    // Don't trigger on YouTube subtitle word spans (overlay.js handles those)
    const range = sel.getRangeAt(0);
    if (range.startContainer?.parentElement?.classList?.contains('lx-yt-word')) {
      return;
    }

    const rect = range.getBoundingClientRect();
    if (!rect.width && !rect.height) return;

    _showQlIcon(text, rect);
  }, 220);
});

document.addEventListener('mousedown', (e) => {
  if (e.target?.id === _QL_ICON_ID) return;
  // Click inside shadow host: the shadow root catches events but target is the host
  if (e.target?.id === _QL_HOST_ID) return;
  // Click inside the shadow card itself (composedPath traverses shadow boundary)
  if (e.composedPath?.().some(el => el?.id === _QL_HOST_ID)) return;
  _removeQlIcon();
  _removeQlOverlay();
});

// ── M27 — Review in the Wild: page highlighting + SRS tooltip ─────────────
// Highlights words in the user's vocabulary with a subtle underline.
// On hover shows a glassmorphism tooltip with the translation and SRS state.
// Word list fetched from Odoo and cached 15 min in chrome.storage.local.

const _LX_CACHE_KEY    = 'lx_word_cache';
const _LX_CACHE_TTL_MS = 15 * 60 * 1000; // 15 minutes

const _REVIEW_CSS = `
  .lx-known-word {
    border-bottom: 1.5px solid rgba(99,102,241,0.5);
    cursor: default;
    border-radius: 1px;
    transition: border-color 0.15s;
  }
  .lx-known-word:hover { border-bottom-color: rgba(99,102,241,0.85); }
  .lx-known-word[data-srs="review"]   { border-bottom-color: rgba(52,211,153,0.55); }
  .lx-known-word[data-srs="review"]:hover { border-bottom-color: rgba(52,211,153,0.9); }
  .lx-known-word[data-srs="learning"] { border-bottom-color: rgba(251,191,36,0.55); }
  .lx-known-word[data-srs="learning"]:hover { border-bottom-color: rgba(251,191,36,0.9); }

  #lx-review-tooltip {
    position: fixed;
    z-index: 2147483646;
    max-width: 240px;
    padding: 10px 13px;
    background: rgba(10,14,28,0.95);
    backdrop-filter: blur(16px) saturate(180%);
    -webkit-backdrop-filter: blur(16px) saturate(180%);
    border: 1px solid rgba(255,255,255,0.11);
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.55), 0 2px 8px rgba(0,0,0,0.4);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 12px;
    color: #e2e8f0;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.12s;
  }
  #lx-review-tooltip.lx-tt-visible { opacity: 1; }
  .lx-tt-word  { font-weight: 700; font-size: 13px; color: #f1f5f9; margin-bottom: 3px; }
  .lx-tt-trans { color: #a5b4fc; font-weight: 600; margin-bottom: 4px; }
  .lx-tt-srs   { color: rgba(255,255,255,0.42); font-size: 11px; }
`;

function _ensureReviewStyles() {
  if (document.getElementById('lx-review-styles')) return;
  const style = document.createElement('style');
  style.id = 'lx-review-styles';
  style.textContent = _REVIEW_CSS;
  document.head.appendChild(style);
}

// ── Word list cache ────────────────────────────────────────────────────────

function _getWordList() {
  return new Promise((resolve) => {
    try {
      chrome.storage.local.get([_LX_CACHE_KEY], (result) => {
        const cached = result[_LX_CACHE_KEY];
        if (cached && cached.generated_at &&
            (Date.now() - cached.generated_at * 1000) < _LX_CACHE_TTL_MS) {
          resolve(cached.words || []);
          return;
        }
        _qlSendMessage({ action: 'lexora-get-learned-words' }, (response) => {
          if (!response || response.status !== 'ok' || !Array.isArray(response.words)) {
            resolve([]);
            return;
          }
          try {
            chrome.storage.local.set({
              [_LX_CACHE_KEY]: { words: response.words, generated_at: response.generated_at },
            });
          } catch (_) { /* non-fatal */ }
          resolve(response.words);
        });
      });
    } catch (_) {
      resolve([]);
    }
  });
}

// ── Word map ───────────────────────────────────────────────────────────────

function _buildWordMap(words) {
  const map = new Map();
  for (const w of words) {
    const key = (w.normalized || w.word || '').toLowerCase().trim();
    if (key.length >= 2 && !map.has(key)) map.set(key, w);
  }
  return map;
}

// ── DOM scanner ────────────────────────────────────────────────────────────

const _LX_SKIP_TAGS = new Set([
  'SCRIPT','STYLE','TEXTAREA','INPUT','CODE','PRE',
  'NOSCRIPT','IFRAME','CANVAS','SVG','MATH','BUTTON','SELECT',
]);

let _lxIsHighlighting = false;

function _wrapMatchesInNode(textNode, wordMap) {
  const text = textNode.nodeValue;
  if (!text || text.trim().length < 2) return false;

  const parts = text.split(/(\s+)/);
  let modified = false;
  const fragment = document.createDocumentFragment();

  for (const part of parts) {
    if (/^\s*$/.test(part)) {
      fragment.appendChild(document.createTextNode(part));
      continue;
    }
    const key = part.toLowerCase().replace(/^[^a-zÀ-ɏͰ-ϿЀ-ӿ]+/i, '')
                                  .replace(/[^a-zÀ-ɏͰ-ϿЀ-ӿ]+$/i, '');
    const entry = key.length >= 2 ? wordMap.get(key) : null;
    if (entry) {
      const span = document.createElement('span');
      span.className = 'lx-known-word';
      span.setAttribute('data-srs',      entry.srs_state || 'null');
      span.setAttribute('data-word',     entry.word);
      span.setAttribute('data-trans-uk', (entry.translations && entry.translations.uk) || '');
      span.setAttribute('data-trans-el', (entry.translations && entry.translations.el) || '');
      span.setAttribute('data-trans-pl', (entry.translations && entry.translations.pl) || '');
      span.setAttribute('data-days',     entry.days_ago != null ? String(entry.days_ago) : '');
      span.textContent = part;
      fragment.appendChild(span);
      modified = true;
    } else {
      fragment.appendChild(document.createTextNode(part));
    }
  }

  if (modified) textNode.parentNode.replaceChild(fragment, textNode);
  return modified;
}

function _highlightPage(wordMap) {
  if (_lxIsHighlighting || !wordMap.size) return;
  _lxIsHighlighting = true;

  try {
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          if (_LX_SKIP_TAGS.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
          if (parent.classList?.contains('lx-known-word')) return NodeFilter.FILTER_REJECT;
          if (parent.classList?.contains('lx-yt-word')) return NodeFilter.FILTER_REJECT;
          if (parent.id === _QL_HOST_ID || parent.id === 'lx-review-tooltip') return NodeFilter.FILTER_REJECT;
          if (parent.closest?.(`#${_QL_HOST_ID}, #lx-review-tooltip`)) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        },
      }
    );

    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) _wrapMatchesInNode(node, wordMap);
  } finally {
    _lxIsHighlighting = false;
  }
}

// ── Tooltip ────────────────────────────────────────────────────────────────

function _showReviewTooltip(entry, anchorEl) {
  let tt = document.getElementById('lx-review-tooltip');
  if (!tt) {
    tt = document.createElement('div');
    tt.id = 'lx-review-tooltip';
    document.body.appendChild(tt);
  }

  const daysAgo = entry.days_ago != null ? entry.days_ago : null;
  const srsLabel = entry.srs_state === 'review'   ? 'Mastered'
                 : entry.srs_state === 'learning' ? 'In progress'
                 : 'New word';
  const timeLabel = daysAgo === 0 ? 'reviewed today'
                  : daysAgo === 1 ? 'reviewed yesterday'
                  : daysAgo > 1  ? `reviewed ${daysAgo} days ago`
                  : 'not yet reviewed';

  const transLines = [];
  if (entry.translations) {
    if (entry.translations.uk) transLines.push(`🇺🇦 ${escHtml(entry.translations.uk)}`);
    if (entry.translations.el) transLines.push(`🇬🇷 ${escHtml(entry.translations.el)}`);
    if (entry.translations.pl) transLines.push(`🇵🇱 ${escHtml(entry.translations.pl)}`);
  }

  tt.innerHTML = `
    <div class="lx-tt-word">${escHtml(entry.word)}</div>
    ${transLines.length ? `<div class="lx-tt-trans">${transLines.join('<span class="lx-tt-sep"> · </span>')}</div>` : ''}
    <div class="lx-tt-srs">${escHtml(srsLabel)} · ${escHtml(timeLabel)}</div>
  `;

  const rect = anchorEl.getBoundingClientRect();
  let left = Math.round(rect.left);
  let top  = Math.round(rect.bottom + 6);
  if (left + 244 > window.innerWidth - 8) left = Math.max(8, window.innerWidth - 252);
  if (top + 90 > window.innerHeight - 8) top = Math.max(8, Math.round(rect.top - 96));

  tt.style.left = `${left}px`;
  tt.style.top  = `${top}px`;
  tt.classList.add('lx-tt-visible');
}

function _hideReviewTooltip() {
  document.getElementById('lx-review-tooltip')?.classList.remove('lx-tt-visible');
}

// ── Hover delegation ───────────────────────────────────────────────────────

document.body.addEventListener('mouseover', (e) => {
  const span = e.target?.closest?.('.lx-known-word');
  if (!span) return;
  _showReviewTooltip({
    word:         span.dataset.word || span.textContent,
    translations: { uk: span.dataset.transUk || '', el: span.dataset.transEl || '' },
    srs_state:    span.dataset.srs !== 'null' ? span.dataset.srs : null,
    days_ago:     span.dataset.days !== ''    ? parseInt(span.dataset.days, 10) : null,
  }, span);
});

document.body.addEventListener('mouseout', (e) => {
  if (e.target?.closest?.('.lx-known-word')) _hideReviewTooltip();
});

// ── Init ───────────────────────────────────────────────────────────────────

let _lxMutationTimer = null;

async function _initHighlighter() {
  _ensureReviewStyles();

  const words = await _getWordList();
  if (!words.length) return;

  const wordMap = _buildWordMap(words);

  const run = () => _highlightPage(wordMap);
  if (typeof requestIdleCallback === 'function') {
    requestIdleCallback(run, { timeout: 2000 });
  } else {
    setTimeout(run, 150);
  }

  const observer = new MutationObserver(() => {
    if (_lxIsHighlighting) return;
    clearTimeout(_lxMutationTimer);
    _lxMutationTimer = setTimeout(() => _highlightPage(wordMap), 500);
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _initHighlighter);
} else {
  _initHighlighter();
}

// ===========================================================================
// M31 — Lexora Writer: active writing assistant (FAB + popup)
// ===========================================================================
// Detects focused <textarea> / [contenteditable] elements, injects a small
// floating "L" FAB beside them, and on click runs the field's text through
// /lexora_api/writer_check → LLM /analyze-writing. The result is rendered in
// a Shadow-DOM popup with an "Apply to text" button that writes the improved
// version back into the input and dispatches input/change events so React,
// Vue, and other SPA frameworks pick up the change.
// ===========================================================================

const _WRITER_FAB_ID    = 'lx-writer-fab';
const _WRITER_HOST_ID   = 'lx-writer-shadow-host';
const _WRITER_MIN_LEN   = 20;
const _WRITER_MAX_LEN   = 4000;     // matches _MAX_WRITER_TEXT on the proxy
const _WRITER_DEBOUNCE  = 100;      // ms — scroll/resize reposition cadence
const _WRITER_FAB_OFFSET = 6;       // px — gap between input edge and FAB

// Eligibility — denylists for the various "this isn't writing" cases.
const _WRITER_DENY_LABEL_RE = /code|monaco|cm[\-_]editor|codemirror|password|search/i;
const _WRITER_DENY_FORM_RE  = /login|sign[ \-]?in|signup|register|password/i;

let _writerEnabled       = true;    // refreshed from chrome.storage.sync
let _writerCurrentInput  = null;
let _writerScrollTimer   = null;

// ── CSS (Shadow-DOM popup + page-level FAB) ────────────────────────────────

const _WRITER_FAB_CSS = `
  #${_WRITER_FAB_ID} {
    position: fixed; z-index: 2147483600;
    width: 32px; height: 32px;
    border-radius: 50%; border: none; cursor: pointer;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: #ffffff; font: 700 16px/32px 'Inter', system-ui, sans-serif;
    text-align: center; padding: 0;
    box-shadow: 0 6px 18px rgba(79, 70, 229, 0.35),
                0 0 0 2px rgba(255, 255, 255, 0.85);
    transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
    opacity: 0; pointer-events: none;
  }
  #${_WRITER_FAB_ID}.lx-visible { opacity: 1; pointer-events: auto; }
  #${_WRITER_FAB_ID}:hover {
    transform: scale(1.08);
    box-shadow: 0 8px 22px rgba(79, 70, 229, 0.5),
                0 0 0 2px rgba(255, 255, 255, 0.95);
  }
  #${_WRITER_FAB_ID}.lx-busy { opacity: 0.7; cursor: wait; }
  #${_WRITER_FAB_ID}.lx-busy:hover { transform: none; }
`;

// Glassmorphism card (Shadow-DOM scope — no global leakage). Mirrors the M28
// flexbox-sandwich pattern with !important flex props so host stylesheets
// can't override the layout (M28-12d).
const _WRITER_CARD_CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
  .lx-writer-card {
    position: absolute;
    width: 380px; max-width: calc(100vw - 24px);
    max-height: 70vh !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
    border-radius: 16px;
    background: rgba(15, 23, 42, 0.92);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(99, 102, 241, 0.4);
    box-shadow: 0 22px 60px rgba(0, 0, 0, 0.45);
    color: #e2e8f0;
    animation: lx-fade-in 160ms ease-out;
  }
  @keyframes lx-fade-in {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .lx-writer-header {
    display: flex; align-items: center; justify-content: space-between;
    gap: 8px;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    cursor: move; user-select: none;
    flex-shrink: 0 !important;
    background: linear-gradient(180deg, rgba(99, 102, 241, 0.18), transparent);
  }
  .lx-writer-title { font-size: 14px; font-weight: 700; color: #ffffff; }
  .lx-writer-status {
    font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 999px;
    background: rgba(99, 102, 241, 0.25); color: #c7d2fe;
    text-transform: uppercase; letter-spacing: 0.4px;
  }
  .lx-writer-status.lx-ok      { background: rgba(34, 197, 94, 0.25);  color: #bbf7d0; }
  .lx-writer-status.lx-error   { background: rgba(239, 68, 68, 0.25);  color: #fecaca; }
  .lx-writer-status.lx-busy    { background: rgba(245, 158, 11, 0.25); color: #fde68a; }
  .lx-writer-scroll {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    padding: 12px 16px;
  }
  .lx-writer-scroll::-webkit-scrollbar { width: 6px; }
  .lx-writer-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.18); border-radius: 4px; }
  .lx-writer-section-title {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px;
    color: #94a3b8; font-weight: 700; margin-bottom: 6px;
  }
  .lx-writer-improved {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px; padding: 10px 12px;
    font-size: 14px; line-height: 1.5; color: #f1f5f9;
    margin-bottom: 14px; white-space: pre-wrap;
  }
  .lx-writer-corrections { list-style: none; margin: 0; padding: 0; }
  .lx-writer-correction {
    margin-bottom: 10px; padding-bottom: 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }
  .lx-writer-correction:last-child { border-bottom: none; }
  .lx-writer-fix {
    font-size: 13px; line-height: 1.5; color: #e2e8f0;
  }
  .lx-writer-wrong   { color: #fca5a5; text-decoration: line-through; }
  .lx-writer-correct { color: #86efac; font-weight: 600; }
  .lx-writer-arrow   { color: #94a3b8; margin: 0 6px; }
  .lx-writer-note {
    font-size: 11px; color: #94a3b8; margin-top: 4px; line-height: 1.45;
  }
  .lx-writer-empty {
    padding: 8px 0;
    font-size: 13px; color: #94a3b8; text-align: center;
  }
  .lx-writer-footer {
    display: flex !important; align-items: center; gap: 8px;
    padding: 10px 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    flex-shrink: 0 !important;
  }
  .lx-writer-privacy {
    flex: 1 1 auto;
    font-size: 10px; color: #64748b; line-height: 1.3;
  }
  .lx-writer-btn {
    border: none; cursor: pointer; padding: 8px 14px; border-radius: 8px;
    font-size: 12px; font-weight: 600;
    transition: transform 100ms ease, opacity 100ms ease;
  }
  .lx-writer-btn:active { transform: scale(0.97); }
  .lx-writer-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .lx-writer-btn-primary {
    background: linear-gradient(135deg, #6366f1, #4f46e5); color: #ffffff;
  }
  .lx-writer-btn-secondary {
    background: rgba(255, 255, 255, 0.08); color: #cbd5e1;
  }
`;

function _ensureWriterStyles() {
  if (document.getElementById('lx-writer-styles')) return;
  const style = document.createElement('style');
  style.id = 'lx-writer-styles';
  style.textContent = _WRITER_FAB_CSS;
  (document.head || document.documentElement).appendChild(style);
}

// ── Eligibility filter ─────────────────────────────────────────────────────
// STRICT — passwords, search, code editors, login forms, and our own Shadow
// DOMs all silently rejected so the FAB never becomes a nuisance.

function _isEligibleInput(el) {
  if (!el || !el.tagName) return false;

  // Never inject into our own overlays (Quick Look card, YouTube subtitle
  // overlay, the writer card itself).
  if (el.closest && (
        el.closest(`#${_QL_HOST_ID}`) ||
        el.closest(`#${_WRITER_HOST_ID}`) ||
        el.closest('.lx-yt-card') ||
        el.closest('.lx-known-word')
  )) return false;

  const tag = el.tagName;
  const isTextarea = tag === 'TEXTAREA';
  const isCE = el.isContentEditable === true;
  if (!isTextarea && !isCE) return false;

  // Text-input textareas only — readonly/disabled rejected.
  if (el.hasAttribute('readonly') || el.hasAttribute('disabled')) return false;
  if (isTextarea && (el.type === 'password' || el.type === 'hidden')) return false;

  // Search bars and ARIA roles that indicate non-writing surfaces.
  if (el.closest('[role="search"]')) return false;
  const role = (el.getAttribute('role') || '').toLowerCase();
  if (role === 'search' || role === 'searchbox' || role === 'spinbutton') return false;

  // Code editors — Monaco, CodeMirror, ACE, github.dev, replit, codesandbox.
  const aria = (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('aria-describedby') || '');
  if (_WRITER_DENY_LABEL_RE.test(aria)) return false;
  if (_WRITER_DENY_LABEL_RE.test((el.className || '').toString())) return false;

  // Code editors typically wrap their textarea in an ancestor with these
  // class hints.
  const codeAncestor = el.closest('.monaco-editor, .CodeMirror, .cm-editor, .ace_editor, [class*="code-editor"]');
  if (codeAncestor) return false;

  // Login / signup / password forms — name attr or id pattern on the form.
  const form = el.form || el.closest('form');
  if (form) {
    const formName = (form.getAttribute('name') || '') + ' ' +
                     (form.id || '') + ' ' +
                     (form.getAttribute('action') || '');
    if (_WRITER_DENY_FORM_RE.test(formName)) return false;
  }

  // Inputs nested inside non-page contexts (e.g. extension popups, iframes
  // we cannot reach).
  if (el.ownerDocument !== document) return false;

  return true;
}

// ── FAB ────────────────────────────────────────────────────────────────────

function _ensureFab() {
  let fab = document.getElementById(_WRITER_FAB_ID);
  if (fab) return fab;
  _ensureWriterStyles();
  fab = document.createElement('button');
  fab.id = _WRITER_FAB_ID;
  fab.type = 'button';
  fab.title = 'Lexora — fix grammar & polish writing';
  fab.textContent = 'L';
  fab.setAttribute('aria-label', 'Lexora writing assistant');
  fab.addEventListener('mousedown', (e) => {
    // Prevent the input from losing focus on FAB click (Chrome behaviour
    // varies — preventDefault on mousedown keeps the input focused so the
    // selection / caret position survives the click).
    e.preventDefault();
  });
  fab.addEventListener('click', _onFabClick);
  document.body.appendChild(fab);
  return fab;
}

function _positionFab(input) {
  const fab = _ensureFab();
  const r = input.getBoundingClientRect();
  // Off-screen → hide.
  if (r.bottom < 0 || r.top > window.innerHeight ||
      r.right < 0 || r.left > window.innerWidth) {
    fab.classList.remove('lx-visible');
    return;
  }
  const left = Math.max(8, Math.min(window.innerWidth - 40, r.right - 32 - _WRITER_FAB_OFFSET));
  const top  = Math.max(8, Math.min(window.innerHeight - 40, r.bottom - 32 - _WRITER_FAB_OFFSET));
  fab.style.left = `${left}px`;
  fab.style.top  = `${top}px`;
  fab.classList.add('lx-visible');
}

function _showFab(input) {
  _writerCurrentInput = input;
  _positionFab(input);
}

function _hideFab() {
  const fab = document.getElementById(_WRITER_FAB_ID);
  if (fab) fab.classList.remove('lx-visible');
  _writerCurrentInput = null;
}

// ── Read / write input value ───────────────────────────────────────────────

function _readInputText(input) {
  if (!input) return '';
  if (input.tagName === 'TEXTAREA') return input.value || '';
  if (input.isContentEditable) return input.innerText || '';
  return '';
}

// Apply the improved text back to the input. For textareas in React-managed
// pages, setting .value directly bypasses React's setter — using the native
// HTMLTextAreaElement prototype setter and dispatching an input event is the
// canonical workaround. For contenteditable, mutating innerText + dispatching
// input/change is sufficient for Vue/Svelte/etc.
function _applyWriterImproved(input, improved) {
  if (!input || !improved) return;
  const isTextarea = input.tagName === 'TEXTAREA';
  if (isTextarea) {
    try {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value'
      )?.set;
      if (nativeSetter) {
        nativeSetter.call(input, improved);
      } else {
        input.value = improved;
      }
    } catch {
      input.value = improved;
    }
  } else if (input.isContentEditable) {
    input.innerText = improved;
  } else {
    return;
  }

  // Both events with bubbles:true so React/Vue/Svelte/Solid all notice the
  // change. React 17+ uses native InputEvent; older pages rely on `change`.
  try {
    input.dispatchEvent(new InputEvent('input', { bubbles: true, data: improved, inputType: 'insertReplacementText' }));
  } catch {
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
  input.dispatchEvent(new Event('change', { bubbles: true }));
}

// ── FAB click → analysis flow ──────────────────────────────────────────────

function _onFabClick() {
  const input = _writerCurrentInput;
  if (!input) return;

  const fab = document.getElementById(_WRITER_FAB_ID);
  const text = _readInputText(input).trim();

  if (text.length < _WRITER_MIN_LEN) {
    _renderWriterOverlay(input, {
      status: 'short',
      message: `Write at least ${_WRITER_MIN_LEN} characters first — currently ${text.length}.`,
    });
    return;
  }
  if (text.length > _WRITER_MAX_LEN) {
    // Soft cap — let the proxy truncate; just warn.
    console.warn('[Lexora Writer] text > 4000 chars — proxy will truncate.');
  }

  fab.classList.add('lx-busy');
  _renderWriterOverlay(input, { status: 'loading' });

  const language = _detectLang(text);
  const context = (input.getAttribute('aria-label') ||
                   input.getAttribute('placeholder') ||
                   '').slice(0, 200);

  _qlSendMessage({
    action: 'lexora-writer-check',
    text,
    language,
    context,
  }, (response) => {
    fab.classList.remove('lx-busy');
    if (!response) {
      _renderWriterOverlay(input, { status: 'error', message: 'No response from background.' });
      return;
    }
    if (response.status === 'context_invalidated') {
      _renderWriterOverlay(input, { status: 'error', message: 'Refresh this tab to restore Lexora.' });
      return;
    }
    if (response.status === 'unauthorized') {
      _renderWriterOverlay(input, { status: 'unauthorized' });
      return;
    }
    if (response.status === 'unavailable') {
      _renderWriterOverlay(input, { status: 'unavailable',
        message: response.message || 'LLM service unavailable.' });
      return;
    }
    if (response.status !== 'ok') {
      _renderWriterOverlay(input, { status: 'error', message: response.message || 'Analysis failed.' });
      return;
    }
    _renderWriterOverlay(input, response);
  });
}

// ── Shadow-DOM popup ───────────────────────────────────────────────────────

function _removeWriterOverlay() {
  const host = document.getElementById(_WRITER_HOST_ID);
  if (host) host.remove();
}

function _renderWriterOverlay(anchorInput, response) {
  _removeWriterOverlay();

  const host = document.createElement('div');
  host.id = _WRITER_HOST_ID;
  host.style.cssText = 'position:fixed;inset:0;width:0;height:0;overflow:visible;z-index:2147483601;';
  const shadow = host.attachShadow({ mode: 'open' });

  const r = anchorInput.getBoundingClientRect();
  const cardLeft = Math.max(8, Math.min(window.innerWidth - 388, r.left));
  const cardTop  = Math.max(8, Math.min(window.innerHeight - 200, r.bottom + 8));

  let statusClass = 'lx-busy';
  let statusText  = 'Analysing…';
  let bodyHtml    = '<div class="lx-writer-empty">Working on it…</div>';
  let showApply   = false;
  let improved    = '';

  if (response.status === 'short') {
    statusClass = 'lx-busy';
    statusText  = 'Too short';
    bodyHtml    = `<div class="lx-writer-empty">${escHtml(response.message || '')}</div>`;
  } else if (response.status === 'unauthorized') {
    statusClass = 'lx-error';
    statusText  = 'Sign in';
    bodyHtml    = '<div class="lx-writer-empty">Please sign in to Lexora first.</div>';
  } else if (response.status === 'unavailable') {
    statusClass = 'lx-error';
    statusText  = 'Unavailable';
    bodyHtml    = `<div class="lx-writer-empty">${escHtml(response.message || 'LLM service unavailable.')}</div>`;
  } else if (response.status === 'error') {
    statusClass = 'lx-error';
    statusText  = 'Error';
    bodyHtml    = `<div class="lx-writer-empty">${escHtml(response.message || 'Something went wrong.')}</div>`;
  } else if (response.status === 'ok') {
    const corrections = Array.isArray(response.corrections) ? response.corrections : [];
    improved = response.improved || '';
    const hasAnything = improved.trim() || corrections.length;
    statusClass = 'lx-ok';
    statusText  = 'Done';

    if (!hasAnything) {
      bodyHtml = '<div class="lx-writer-empty">Nothing to fix — your writing looks good!</div>';
    } else {
      const parts = [];
      if (improved.trim()) {
        parts.push(`
          <div class="lx-writer-section-title">Improved version</div>
          <div class="lx-writer-improved">${escHtml(improved)}</div>
        `);
        showApply = true;
      }
      if (corrections.length) {
        const rows = corrections.map((c) => `
          <li class="lx-writer-correction">
            <div class="lx-writer-fix">
              <span class="lx-writer-wrong">${escHtml(c.wrong || '')}</span>
              <span class="lx-writer-arrow">→</span>
              <span class="lx-writer-correct">${escHtml(c.correct || '')}</span>
            </div>
            ${c.note ? `<div class="lx-writer-note">${escHtml(c.note)}</div>` : ''}
          </li>
        `).join('');
        parts.push(`
          <div class="lx-writer-section-title">Corrections</div>
          <ul class="lx-writer-corrections">${rows}</ul>
        `);
      }
      bodyHtml = parts.join('');
    }
  } else if (response.status === 'loading') {
    /* defaults already set */
  }

  shadow.innerHTML = `
    <style>${_WRITER_CARD_CSS}</style>
    <div class="lx-writer-card" style="left:${cardLeft}px;top:${cardTop}px;">
      <div class="lx-writer-header">
        <span class="lx-writer-title">✦ Lexora Writer</span>
        <span class="lx-writer-status ${statusClass}">${escHtml(statusText)}</span>
      </div>
      <div class="lx-writer-scroll">${bodyHtml}</div>
      <div class="lx-writer-footer">
        <span class="lx-writer-privacy">Text is sent to your Lexora server for analysis.</span>
        ${showApply
          ? '<button class="lx-writer-btn lx-writer-btn-primary" id="lx-writer-apply">Apply to text</button>'
          : ''}
        <button class="lx-writer-btn lx-writer-btn-secondary" id="lx-writer-close">Close</button>
      </div>
    </div>
  `;

  document.body.appendChild(host);

  shadow.getElementById('lx-writer-close')?.addEventListener('click', _removeWriterOverlay);
  if (showApply) {
    shadow.getElementById('lx-writer-apply')?.addEventListener('click', () => {
      _applyWriterImproved(anchorInput, improved);
      _removeWriterOverlay();
      // Brief confirmation toast.
      try { showLexoraToast('ok', 'Applied to text'); } catch {}
    });
  }

  // Click-outside-to-close (uses composedPath so clicks inside the shadow
  // root don't trigger the close).
  const onDocClick = (e) => {
    if (e.composedPath && e.composedPath().some((el) => el?.id === _WRITER_HOST_ID)) return;
    _removeWriterOverlay();
    document.removeEventListener('mousedown', onDocClick, true);
  };
  setTimeout(() => document.addEventListener('mousedown', onDocClick, true), 0);

  // Drag the card by its header (same pattern as M28-17 Quick Look).
  _makeWriterDraggable(shadow);
}

function _makeWriterDraggable(shadow) {
  const card = shadow.querySelector('.lx-writer-card');
  const header = shadow.querySelector('.lx-writer-header');
  if (!card || !header) return;
  let dragging = false, startX = 0, startY = 0, baseLeft = 0, baseTop = 0;

  header.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('button')) return;
    e.preventDefault();
    dragging = true;
    startX = e.clientX; startY = e.clientY;
    baseLeft = parseFloat(card.style.left) || 0;
    baseTop  = parseFloat(card.style.top)  || 0;
  });

  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX, dy = e.clientY - startY;
    const newLeft = Math.max(8, Math.min(window.innerWidth - 388, baseLeft + dx));
    const newTop  = Math.max(8, Math.min(window.innerHeight - 80,  baseTop  + dy));
    card.style.left = `${newLeft}px`;
    card.style.top  = `${newTop}px`;
  });

  document.addEventListener('mouseup', () => { dragging = false; });
}

// ── Init: focusin/focusout, scroll/resize, storage flag ────────────────────

function _onWriterFocusIn(e) {
  if (!_writerEnabled) return;
  const t = e.target;
  if (!_isEligibleInput(t)) return;
  _showFab(t);
}

function _onWriterFocusOut(e) {
  // Delay the hide so the FAB click handler can fire before blur kills it.
  setTimeout(() => {
    const active = document.activeElement;
    if (active && _isEligibleInput(active)) {
      // User just moved focus to another eligible field.
      _showFab(active);
      return;
    }
    // If the user is now interacting with the FAB or the popup, keep it.
    if (active && (active.id === _WRITER_FAB_ID || active.closest?.(`#${_WRITER_HOST_ID}`))) {
      return;
    }
    _hideFab();
  }, 150);
}

function _onWriterScrollOrResize() {
  if (!_writerCurrentInput) return;
  clearTimeout(_writerScrollTimer);
  _writerScrollTimer = setTimeout(() => {
    if (_writerCurrentInput && _isEligibleInput(_writerCurrentInput)) {
      _positionFab(_writerCurrentInput);
    }
  }, _WRITER_DEBOUNCE);
}

function _initWriter() {
  // Refresh enabled flag from storage; default ON when key absent.
  try {
    chrome.storage.sync.get('lexora_writer_enabled', (cfg) => {
      _writerEnabled = (cfg && cfg.lexora_writer_enabled !== false);
    });
    chrome.storage.onChanged?.addListener((changes, area) => {
      if (area === 'sync' && 'lexora_writer_enabled' in changes) {
        _writerEnabled = changes.lexora_writer_enabled.newValue !== false;
        if (!_writerEnabled) _hideFab();
      }
    });
  } catch {
    /* chrome.storage unavailable — keep default */
  }

  document.addEventListener('focusin',  _onWriterFocusIn,  true);
  document.addEventListener('focusout', _onWriterFocusOut, true);
  window.addEventListener('scroll',  _onWriterScrollOrResize, true);
  window.addEventListener('resize',  _onWriterScrollOrResize);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _initWriter);
} else {
  _initWriter();
}
