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
