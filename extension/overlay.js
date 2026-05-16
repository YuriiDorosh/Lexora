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

// ── M35 — Multi-word selection state ───────────────────────────────────────
//
// _lxSwallowNextClick: set by the mouseup → phrase capture branch right
//                      before the upcoming click event fires on the anchor
//                      span. _onWordClick drains it on entry so the
//                      single-word click handler doesn't double-fire after a
//                      multi-word drag. The browser's hard mouseup → click
//                      contract is what we're working around — see ADR-034
//                      sub-decision 35d.
let _lxSwallowNextClick = false;

// _lxFirewallBound: WeakSet of container elements that already have the
//                   capture-phase firewall trio bound. Idempotency guard for
//                   _bindCaptureFirewall — _attachCaptionObserver can be
//                   called many times against the same element (initial
//                   attach + every yt-navigate-finish + every docObserver
//                   poke). A new container post SPA-nav lands as a fresh
//                   element so binding kicks back in naturally; the old
//                   element drops out of the WeakSet when GC'd.
const _lxFirewallBound = new WeakSet();

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
  /* M35 adds user-select: text on the caption subtree so a drag
     across our wrapped spans extends a native browser selection.
     YT applies user-select:none on the .html5-video-container subtree
     by default; we override on the caption sub-tree only so the rest
     of the player surface (controls, video frame) keeps its
     non-selectable behaviour. Both the standard property and the
     -webkit- prefix because YT serves different builds depending on
     the UA. */
  .ytp-caption-window-container,
  .ytp-captions-container,
  .ytp-caption-segment,
  .captions-text {
    pointer-events: auto !important;
    user-select: text !important;
    -webkit-user-select: text !important;
  }

  /* ── Interactive word spans ───────────────────────────── */
  /* M35: cursor: text by default signals the drag-to-select
     affordance; the :hover rule below restores cursor: pointer for
     stationary hovers so the click affordance is still legible.
     During an active drag the browser shows the native I-beam
     regardless of CSS, so both UX modes are covered. */
  .${_WORD_CLASS} {
    cursor: text !important;
    user-select: text !important;
    -webkit-user-select: text !important;
    border-radius: 3px;
    border-bottom: 1px dashed rgba(129, 140, 248, 0.6) !important;
    transition: background 0.2s, color 0.2s;
    padding: 1px 1px;
    pointer-events: auto !important;
  }
  .${_WORD_CLASS}:hover {
    cursor: pointer !important;
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

  /* M32 — Slang/Idiom Explainer */
  .lx-yt-slang-btn {
    display:block; width:100%; margin-top:6px; padding:6px 0;
    background: rgba(245,158,11,0.15);
    border: 1px solid rgba(245,158,11,0.4);
    border-radius:8px; color:#fde68a; font-size:12px; font-weight:600;
    cursor: pointer !important; pointer-events: auto !important;
    transition: background 0.15s;
  }
  .lx-yt-slang-btn:hover { background: rgba(245,158,11,0.3); }
  .lx-yt-slang-btn:disabled { opacity:0.5; cursor:default !important; }

  .lx-yt-slang-block {
    display:none; margin-top:8px; padding:10px 12px;
    background: rgba(245,158,11,0.08);
    border-left: 3px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    font-size:12px; line-height:1.6; color:#fef3c7;
  }
  .lx-yt-slang-block.lx-visible { display:block; }
  .lx-yt-slang-kind {
    display:inline-block; margin-bottom:6px;
    padding:1px 8px; border-radius:999px;
    background: rgba(245,158,11,0.25); color:#fbbf24;
    font-size:10px; font-weight:700;
    text-transform:uppercase; letter-spacing:0.5px;
  }
  .lx-yt-slang-figurative {
    margin:4px 0 6px; font-size:13px; font-weight:600; color:#fef3c7;
  }
  .lx-yt-slang-literal {
    margin-bottom:6px; font-size:11px; font-style:italic;
    color:#fde68a; opacity:0.85;
  }
  .lx-yt-slang-example {
    margin-top:6px; padding:6px 10px;
    background: rgba(255,255,255,0.04);
    border-radius:6px;
    font-size:11px; font-style:italic; color:#fef3c7;
  }
  .lx-yt-slang-uncertain {
    display:block; margin-top:6px;
    font-size:11px; font-style:italic; color:#f87171;
  }

  /* M33 — Webpage Shadowing (teal/rose accent) */
  .lx-yt-shadow-btn {
    display:block; width:100%; margin-top:6px; padding:6px 0;
    background: rgba(20, 184, 166, 0.15);
    border: 1px solid rgba(20, 184, 166, 0.4);
    border-radius:8px; color:#5eead4; font-size:12px; font-weight:600;
    cursor: pointer !important; pointer-events: auto !important;
    transition: background 0.15s;
  }
  .lx-yt-shadow-btn:hover    { background: rgba(20, 184, 166, 0.3); }
  .lx-yt-shadow-btn:disabled { opacity:0.5; cursor:default !important; }

  .lx-yt-shadow-block {
    display:none; margin-top:8px; padding:10px 12px;
    background: rgba(20, 184, 166, 0.06);
    border-left: 3px solid #14b8a6;
    border-radius: 0 8px 8px 0;
    font-size:12px; line-height:1.6; color:#e0f2fe;
  }
  .lx-yt-shadow-block.lx-visible { display:block; }

  .lx-yt-shadow-reference {
    margin-bottom:8px; padding:6px 10px;
    background: rgba(255, 255, 255, 0.04);
    border-radius:6px;
    font-size:13px; line-height:1.5; color:#f1f5f9;
  }
  .lx-yt-shadow-word { display:inline; }
  .lx-yt-shadow-word-missed {
    color:#fca5a5; text-decoration: line-through;
    text-decoration-thickness: 2px;
  }
  .lx-yt-shadow-word-mispron {
    color:#fbbf24;
    text-decoration: underline wavy;
    text-decoration-color: #f59e0b;
  }

  .lx-yt-shadow-controls {
    display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px;
  }
  .lx-yt-shadow-play-btn,
  .lx-yt-shadow-record-btn {
    flex:1 1 auto; padding:6px 10px;
    border-radius:8px; font-size:12px; font-weight:600;
    cursor:pointer !important; pointer-events:auto !important;
    border:1px solid rgba(255,255,255,0.18);
    background: rgba(255, 255, 255, 0.06);
    color:#cbd5e1;
    user-select:none;
    transition: background 0.15s, box-shadow 0.15s;
  }
  .lx-yt-shadow-play-btn:hover    { background: rgba(255, 255, 255, 0.12); }
  .lx-yt-shadow-play-btn:disabled { opacity:0.5; cursor:default !important; }
  .lx-yt-shadow-record-btn       { color:#fda4af; }
  .lx-yt-shadow-record-btn:hover { background: rgba(244, 63, 94, 0.16); }
  .lx-yt-shadow-record-btn.lx-recording {
    background: rgba(244, 63, 94, 0.28); color:#ffffff;
    box-shadow: 0 0 0 2px rgba(244, 63, 94, 0.55),
                0 0 16px rgba(244, 63, 94, 0.4);
    animation: lx-yt-rec-pulse 1.4s ease-in-out infinite;
  }
  @keyframes lx-yt-rec-pulse {
    0%, 100% { box-shadow: 0 0 0 2px rgba(244, 63, 94, 0.55),
                            0 0 12px rgba(244, 63, 94, 0.35); }
    50%      { box-shadow: 0 0 0 2px rgba(244, 63, 94, 0.85),
                            0 0 22px rgba(244, 63, 94, 0.6);  }
  }

  .lx-yt-shadow-status { margin-top:4px; font-size:11px; color:#94a3b8; min-height:14px; }
  .lx-yt-shadow-result { margin-top:8px; }
  .lx-yt-shadow-score {
    display:inline-block; padding:4px 10px; border-radius:999px;
    font-size:14px; font-weight:700; margin-right:8px;
  }
  .lx-yt-shadow-score-green { background: rgba(34, 197, 94, 0.25);  color:#bbf7d0; }
  .lx-yt-shadow-score-amber { background: rgba(245, 158, 11, 0.25); color:#fde68a; }
  .lx-yt-shadow-score-red   { background: rgba(244, 63, 94, 0.25);  color:#fda4af; }
  .lx-yt-shadow-feedback {
    margin-top:8px; padding:6px 10px;
    background: rgba(20, 184, 166, 0.08);
    border-radius:6px;
    font-size:12px; font-style:italic; color:#ccfbf1;
  }
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

// M32 — YouTube-flavour slang block renderer (mirrors content.js's
// _renderSlangBlock; uses .lx-yt-* classes scoped to overlay.js's CSS).
const _YT_SLANG_KIND_LABELS = {
  idiom: 'Idiom', slang: 'Slang', phrasal_verb: 'Phrasal Verb',
  literal: 'Literal', unknown: 'Unknown',
};
function _renderYtSlangBlock(container, resp) {
  if (!container) return;
  if (!resp) {
    container.innerHTML = '<em>No response from background.</em>';
    container.classList.add('lx-visible'); return;
  }
  if (resp.status === 'context_invalidated') {
    container.innerHTML = '<em>Refresh this tab to restore Lexora.</em>';
    container.classList.add('lx-visible'); return;
  }
  if (resp.status === 'unauthorized') {
    container.innerHTML = '<em>Please sign in to Lexora first.</em>';
    container.classList.add('lx-visible'); return;
  }
  if (resp.status === 'unavailable') {
    container.innerHTML = `<em>${_escHtml(resp.message || 'LLM unavailable.')}</em>`;
    container.classList.add('lx-visible'); return;
  }
  if (resp.status === 'error') {
    container.innerHTML = `<em>${_escHtml(resp.message || 'Could not look up phrase.')}</em>`;
    container.classList.add('lx-visible'); return;
  }
  const kind = (resp.kind || 'unknown').toLowerCase();
  const figurative = (resp.figurative_meaning || '').trim();
  const literal    = (resp.literal_meaning    || '').trim();
  const example    = (resp.example            || '').trim();
  const confidence = (resp.confidence || 'low').toLowerCase();
  const kindLabel  = _YT_SLANG_KIND_LABELS[kind] || _YT_SLANG_KIND_LABELS.unknown;

  if (kind === 'literal') {
    let html = `<span class="lx-yt-slang-kind">${_escHtml(kindLabel)}</span>`;
    html += `<div class="lx-yt-slang-figurative">This phrase translates literally — no figurative meaning.</div>`;
    if (literal) html += `<div class="lx-yt-slang-literal">${_escHtml(literal)}</div>`;
    container.innerHTML = html;
    container.classList.add('lx-visible'); return;
  }

  let html = `<span class="lx-yt-slang-kind">${_escHtml(kindLabel)}</span>`;
  if (figurative) html += `<div class="lx-yt-slang-figurative">${_escHtml(figurative)}</div>`;
  if (literal && literal !== figurative) {
    html += `<div class="lx-yt-slang-literal">Literally: ${_escHtml(literal)}</div>`;
  }
  if (example) {
    html += `<div class="lx-yt-slang-example">"${_escHtml(example)}"</div>`;
  }
  if (confidence === 'low') {
    html += `<em class="lx-yt-slang-uncertain">⚠ AI is uncertain — consider checking a dictionary.</em>`;
  }
  if (!figurative && !literal && !example) {
    html += `<em>Could not classify this phrase.</em>`;
  }
  container.innerHTML = html;
  container.classList.add('lx-visible');
}

// M33 — YouTube-flavour shadowing controls + result renderer.
// Mirrors content.js's _renderShadowControls / _renderShadowResult but
// scoped to the .lx-yt-* class prefix and overlay.querySelector tree.

// M33-S5-FIX: pivoted from hold-to-record to click-to-toggle.
// _YT_SHADOW_MIN_HOLD_MS is no longer used (no debounce needed for toggle).
const _YT_SHADOW_REC_MAX_MS  = 30 * 1000;
const _YT_SHADOW_WORD_TOKEN_RE = /[\wÀ-ɏͰ-ϿЀ-ӿ'-]+/gu;

function _ytShadowB64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function _ytShadowScoreTier(score) {
  if (score >= 80) return 'green';
  if (score >= 60) return 'amber';
  return 'red';
}

function _renderYtShadowAnnotated(refEl, referenceText, missed, mispron) {
  const missedSet  = new Set((missed  || []).map((w) => String(w).toLowerCase()));
  const mispronSet = new Set((mispron || []).map((w) => String(w).toLowerCase()));
  let out = '';
  let lastIndex = 0;
  _YT_SHADOW_WORD_TOKEN_RE.lastIndex = 0;
  let m;
  while ((m = _YT_SHADOW_WORD_TOKEN_RE.exec(referenceText)) !== null) {
    const word = m[0];
    const start = m.index;
    if (start > lastIndex) out += _escHtml(referenceText.slice(lastIndex, start));
    const lower = word.toLowerCase();
    let cls = 'lx-yt-shadow-word';
    if (missedSet.has(lower))      cls += ' lx-yt-shadow-word-missed';
    else if (mispronSet.has(lower)) cls += ' lx-yt-shadow-word-mispron';
    out += `<span class="${cls}">${_escHtml(word)}</span>`;
    lastIndex = start + word.length;
  }
  if (lastIndex < referenceText.length) {
    out += _escHtml(referenceText.slice(lastIndex));
  }
  refEl.innerHTML = out;
}

function _renderYtShadowResult(resultEl, refEl, referenceText, resp) {
  const score = Number.isFinite(resp.score) ? Math.max(0, Math.min(100, Math.round(resp.score))) : 0;
  const missed   = Array.isArray(resp.missed_words)        ? resp.missed_words        : [];
  const mispron  = Array.isArray(resp.mispronounced_words) ? resp.mispronounced_words : [];
  const feedback = (resp.feedback || '').toString().trim();
  const tier  = _ytShadowScoreTier(score);

  if (refEl) _renderYtShadowAnnotated(refEl, referenceText, missed, mispron);

  let html = `
    <div>
      <span class="lx-yt-shadow-score lx-yt-shadow-score-${tier}">${score}/100</span>
      <span style="opacity:0.7;font-size:11px;">
        ${missed.length} missed · ${mispron.length} mispronounced
      </span>
    </div>
  `;
  if (feedback) {
    html += `<div class="lx-yt-shadow-feedback">${_escHtml(feedback)}</div>`;
  }
  resultEl.innerHTML = html;
}

function _renderYtShadowControls(rootEl, container, referenceText, language) {
  container.innerHTML = `
    <div class="lx-yt-shadow-reference" id="lx-yt-shadow-ref">${_escHtml(referenceText)}</div>
    <div class="lx-yt-shadow-controls">
      <button class="lx-yt-shadow-play-btn"   id="lx-yt-shadow-play">▶ Play Original</button>
      <button class="lx-yt-shadow-record-btn" id="lx-yt-shadow-record">🎙 Start Recording</button>
    </div>
    <div class="lx-yt-shadow-status" id="lx-yt-shadow-status">Hear the model, then click Start Recording. Click Stop when you are done.</div>
    <div class="lx-yt-shadow-result" id="lx-yt-shadow-result"></div>
  `;
  container.classList.add('lx-visible');

  const playBtn  = rootEl.querySelector('#lx-yt-shadow-play');
  const recBtn   = rootEl.querySelector('#lx-yt-shadow-record');
  const statusEl = rootEl.querySelector('#lx-yt-shadow-status');
  const resultEl = rootEl.querySelector('#lx-yt-shadow-result');
  const refEl    = rootEl.querySelector('#lx-yt-shadow-ref');

  let _audioEl = null;
  if (playBtn) {
    playBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      playBtn.disabled = true;
      const orig = playBtn.textContent;
      playBtn.textContent = 'Loading…';
      statusEl.textContent = 'Fetching pronunciation…';
      _sendMessage({ action: 'lexora-shadow-tts', text: referenceText, language }, (resp) => {
        if (!resp || resp.status !== 'ok' || !resp.audio_b64) {
          playBtn.textContent = orig;
          playBtn.disabled = false;
          statusEl.textContent = (resp && resp.message) || 'Could not load audio.';
          return;
        }
        try {
          const blob = new Blob([_ytShadowB64ToBytes(resp.audio_b64)],
                                { type: resp.mime_type || 'audio/mpeg' });
          if (_audioEl) {
            try { _audioEl.pause(); } catch {}
            try { URL.revokeObjectURL(_audioEl.src); } catch {}
          }
          _audioEl = new Audio(URL.createObjectURL(blob));
          _audioEl.onended = () => {
            playBtn.textContent = orig; playBtn.disabled = false;
            statusEl.textContent = 'Click Start Recording when you are ready.';
          };
          _audioEl.onerror = () => {
            playBtn.textContent = orig; playBtn.disabled = false;
            statusEl.textContent = 'Audio playback failed.';
          };
          playBtn.textContent = '🔊 Playing…';
          statusEl.textContent = 'Listening to the model…';
          _audioEl.play();
        } catch (err) {
          playBtn.textContent = orig; playBtn.disabled = false;
          statusEl.textContent = `Audio decode failed: ${err && err.message || err}`;
        }
      });
    });
  }

  // ── Click-to-toggle Record ────────────────────────────────────────────
  // Pivot from hold-to-record (M33-S5 first cut). YouTube overlay had the
  // same micro-movement issue as the QL overlay; toggle is robust and
  // mirrors the QL implementation exactly.
  let _autoStopTimer = null;
  let _isRecording = false;

  function _stopRecording() {
    if (!_isRecording) return;
    _isRecording = false;
    if (_autoStopTimer) { clearTimeout(_autoStopTimer); _autoStopTimer = null; }

    recBtn.classList.remove('lx-recording');
    recBtn.textContent = 'Analysing…';
    recBtn.disabled = true;
    statusEl.textContent = 'Transcribing your audio…';

    _sendMessage({ action: 'lexora-mic-stop' }, (resp) => {
      if (!resp || resp.status !== 'ok' || !resp.audio_b64) {
        recBtn.textContent = '🎙 Start Recording';
        recBtn.disabled = false;
        statusEl.textContent = (resp && resp.message) || 'Recording failed.';
        return;
      }
      statusEl.textContent = 'Evaluating with AI…';
      _sendMessage({
        action:         'lexora-shadow-evaluate',
        audio_b64:      resp.audio_b64,
        mime_type:      resp.mime_type,
        reference_text: referenceText,
        language,
      }, (evalResp) => {
        recBtn.textContent = '🎙 Start Recording';
        recBtn.disabled = false;
        if (!evalResp) {
          statusEl.textContent = 'No response from server.'; return;
        }
        if (evalResp.status === 'unauthorized') {
          statusEl.textContent = 'Sign in to Lexora first.'; return;
        }
        if (evalResp.status === 'unavailable') {
          statusEl.textContent = (evalResp.message || 'Service unavailable.'); return;
        }
        if (evalResp.status !== 'ok') {
          statusEl.textContent = (evalResp.message || 'Evaluation failed.'); return;
        }
        statusEl.textContent = `Heard: "${evalResp.transcript || '(silence)'}"`;
        _renderYtShadowResult(resultEl, refEl, referenceText, evalResp);
      });
    });
  }

  function _onRecordToggle(e) {
    e.preventDefault();
    e.stopPropagation();

    if (_isRecording) {
      _stopRecording();
      return;
    }

    _isRecording = true;
    recBtn.classList.add('lx-recording');
    recBtn.textContent = '⏹ Stop Recording';
    statusEl.textContent = 'Recording… click Stop when you are done.';

    _sendMessage({ action: 'lexora-mic-start' }, (resp) => {
      if (!resp || resp.status !== 'ok') {
        _isRecording = false;
        recBtn.classList.remove('lx-recording');
        recBtn.textContent = '🎙 Start Recording';
        statusEl.textContent = (resp && resp.message) ||
          'Microphone not available. Open the extension Options page to grant permission.';
        return;
      }
      // 30 s safety auto-stop — mirrors the QL implementation. If the
      // user forgets to click Stop we don't record forever.
      _autoStopTimer = setTimeout(() => {
        if (_isRecording) {
          statusEl.textContent = 'Auto-stopped after 30 s — analysing…';
          _stopRecording();
        }
      }, _YT_SHADOW_REC_MAX_MS);
    });
  }

  if (recBtn) {
    recBtn.addEventListener('click', _onRecordToggle);
  }
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

// ── M35 — Phrase normalisation + capture firewall ─────────────────────────
//
// _normalisePhrase mirrors the regex used in _onWordClick's single-word
// path: collapse internal whitespace, trim, strip outer punctuation. Internal
// apostrophes (don't) and hyphens (mother-in-law) are deliberately PRESERVED
// because both are part of the lookup key — `language.entry.normalized_text`
// stores them. See ADR-034 sub-decision 35e.
function _normalisePhrase(s) {
  return (s || '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^[.,!?;:'"()\[\]{}\-–—]+|[.,!?;:'"()\[\]{}\-–—]+$/g, '')
    .trim();
}

// _bindCaptureFirewall(root): three capture-phase listeners bound on the
// persistent caption container. Each one early-returns unless the event
// target is inside a wrapped word span; for caption-area events, calls
// e.stopPropagation() ONLY (never preventDefault — that would kill native
// selection-extension). YT's player listeners are bubble-phase, so a
// capture-phase stop aborts them entirely. See ADR-034 sub-decisions
// 35b + 35c.
//
// The mouseup listener additionally captures the post-drag selection via
// queueMicrotask: deferred one microtask so the browser finalises the
// selection range before we read it. A multi-word selection sets the
// _lxSwallowNextClick flag (so the per-span click handler that fires next
// doesn't double-process) and routes through _triggerPhraseOverlay.
function _bindCaptureFirewall(root) {
  if (!root) return false;
  if (_lxFirewallBound.has(root)) return false;

  const _firewall = (e) => {
    // Only firewall events that originated inside a wrapped word span.
    // Plain clicks elsewhere in the player (controls bar, video frame,
    // caption whitespace between segments) bubble normally so YT's own
    // play/pause toggle and controls stay intact.
    const target = e.target;
    if (!target || typeof target.closest !== 'function') return;
    if (!target.closest('.' + _WORD_CLASS)) return;
    e.stopPropagation();
    // INTENTIONALLY no preventDefault — preserving the browser's native
    // selection-extension on mousemove during a drag.
  };

  root.addEventListener('mousedown', _firewall, { capture: true });
  root.addEventListener('mousemove', _firewall, { capture: true });

  root.addEventListener('mouseup', (e) => {
    const target = e.target;
    if (!target || typeof target.closest !== 'function') return;
    const anchor = target.closest('.' + _WORD_CLASS);
    if (!anchor) return;
    e.stopPropagation();

    // Defer one microtask so getSelection() reflects the FINAL extended
    // range. Without this, browsers occasionally return an empty string
    // because the selection extension hasn't settled yet.
    queueMicrotask(() => {
      let raw = '';
      try { raw = (window.getSelection() || '').toString(); } catch (_) {}
      const phrase = _normalisePhrase(raw);
      if (!phrase) return;                       // empty selection — click flow takes over
      if (!/\s/.test(phrase)) return;            // single token — click flow takes over

      _lxSwallowNextClick = true;
      _triggerPhraseOverlay(phrase, anchor);

      // Clear the blue highlight so it doesn't linger while the user reads
      // the Quick Look card.
      try { window.getSelection().removeAllRanges(); } catch (_) {}
    });
  }, { capture: true });

  _lxFirewallBound.add(root);
  console.log('[Lexora] M35 capture firewall bound on:',
    root.className || root.tagName);
  return true;
}

// Shared body for the Quick Look open path. Called from BOTH _onWordClick
// (single-word click) AND _triggerPhraseOverlay (multi-word drag). Extracted
// to keep the M24 single-word path byte-identical to its pre-M35 behaviour
// (the per-source-label diagnostic strings differentiate the log lines).
function _openLookupOverlay(word, sourceLabel) {
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
    console.warn(`[Lexora] define response timeout (${sourceLabel}) — showing actions without definition`);
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
        console.warn(`[Lexora] define lastError (${sourceLabel}):`, chrome.runtime.lastError.message);
        _showOverlay(word, wasPaused, timestamp, lang, video, { status: 'error', translations: [] });
        return;
      }
      console.log(`[Lexora] define response (${sourceLabel}) received:`, response);
      _showOverlay(word, wasPaused, timestamp, lang, video, response || { status: 'empty', translations: [] });
    }
  );
}

// M35 — drag-select multi-word phrase entry point. Called from the
// mouseup firewall after _normalisePhrase confirms the selection has
// ≥1 internal space. The anchorSpan is the last-touched word span at
// the drag's release point; passed for future positional anchoring
// (current _showOverlay centres the card on the viewport so the
// anchor is informational only).
function _triggerPhraseOverlay(phrase, anchorSpan) {
  console.log('[Lexora] Phrase selected:', phrase,
    anchorSpan ? `(anchor: ${anchorSpan.textContent})` : '');
  _openLookupOverlay(phrase, 'phrase');
}

function _onWordClick(e) {
  // M35 — single-word click suppression after a multi-word drag.
  // The browser's mouseup→click contract delivers a click on the anchor
  // span right after our drag completes. If _lxSwallowNextClick is set,
  // we drain it here and short-circuit so the single-word flow doesn't
  // re-fire the lookup with just the anchor word.
  if (_lxSwallowNextClick) {
    _lxSwallowNextClick = false;
    e.stopPropagation();
    e.preventDefault();
    return;
  }

  e.stopPropagation();
  e.preventDefault();

  const raw = e.target.textContent || '';
  // Strip leading/trailing punctuation for cleaner lookup
  const word = raw.replace(/^[\s.,!?;:'"()\[\]{}\-–—]+|[\s.,!?;:'"()\[\]{}\-–—]+$/g, '').trim();
  if (!word) return;

  console.log('[Lexora] Word clicked:', word);
  _openLookupOverlay(word, 'word');
}

const _LANG_NAMES = { en: 'English', uk: 'Ukrainian', el: 'Greek', pl: 'Polish' };

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
          ${showActions ? `<div class="lx-yt-slang-block"   id="lx-yt-slang"></div>`   : ''}
          ${showActions ? `<div class="lx-yt-shadow-block"  id="lx-yt-shadow"></div>`  : ''}
        </div>
        ${showActions ? `
        <div class="lx-yt-footer">
          <div class="lx-yt-actions">
            <button class="lx-yt-add-btn" id="lx-yt-add">➕ Add to Vocabulary</button>
            <button class="lx-yt-resume-btn" id="lx-yt-resume">▶ Resume</button>
          </div>
          <button class="lx-yt-explain-btn" id="lx-yt-explain">Explain Grammar</button>
          <button class="lx-yt-slang-btn"   id="lx-yt-explain-slang">💡 Explain Slang/Idiom</button>
          <button class="lx-yt-shadow-btn"  id="lx-yt-practice-shadow">🎤 Practice Pronunciation</button>
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

  // M32 — Explain Slang/Idiom
  const slangBtn   = overlay.querySelector('#lx-yt-explain-slang');
  const slangBlock = overlay.querySelector('#lx-yt-slang');
  if (slangBtn && slangBlock) {
    slangBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      slangBtn.disabled = true;
      const originalLabel = slangBtn.textContent;
      slangBtn.textContent = 'Looking up…';
      const timer = setTimeout(() => {
        slangBlock.innerHTML = '<em>LLM timed out — try again.</em>';
        slangBlock.classList.add('lx-visible');
        slangBtn.textContent = originalLabel;
        slangBtn.disabled = false;
      }, 65000);

      chrome.storage.sync.get('lexora_native_language', (cfg) => {
        const nativeLang = (cfg && cfg.lexora_native_language) || 'en';
        _sendMessage({
          action: 'lexora-explain-slang',
          phrase: word,
          source_language: lang,
          native_language: nativeLang,
        }, (resp) => {
          clearTimeout(timer);
          _renderYtSlangBlock(slangBlock, resp);
          slangBtn.textContent = originalLabel;
          slangBtn.disabled = false;
          const scrollEl = overlay.querySelector('.lx-yt-scroll');
          if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
        });
      });
    });
  }

  // M33 — Practice Pronunciation (Webpage Shadowing)
  const practiceBtn = overlay.querySelector('#lx-yt-practice-shadow');
  const shadowBlock = overlay.querySelector('#lx-yt-shadow');
  if (practiceBtn && shadowBlock) {
    practiceBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (!shadowBlock.classList.contains('lx-visible')) {
        _renderYtShadowControls(overlay, shadowBlock, word, lang);
      }
      const scrollEl = overlay.querySelector('.lx-yt-scroll');
      if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
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
    // M35: bind the capture-phase firewall + drag-to-select listener trio
    // on the persistent container. WeakSet guard inside _bindCaptureFirewall
    // makes this idempotent on repeated calls against the same element.
    _bindCaptureFirewall(container);
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
