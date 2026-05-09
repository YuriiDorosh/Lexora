'use strict';

// ---------------------------------------------------------------------------
// M23 — Contextual Capture & Smart Selection
//
// Right-clicking selected text shows "Add to Lexora" in the context menu.
// On click: capture selection + surrounding sentence → POST /lexora_api/add_word
// directly from the service worker (no CORS restriction in background context).
// Stores captured data in chrome.storage.session so the popup pre-fills if
// opened within 30 seconds of the context menu action.
// Badge feedback: ✓ saved (green) | = duplicate (amber) | ! error (red)
// ---------------------------------------------------------------------------

const DEFAULT_BASE_URL = 'http://localhost:5433';
const ADD_WORD_PATH = '/lexora_api/add_word';

async function getBaseUrl() {
  return new Promise(resolve => {
    chrome.storage.sync.get(['lexoraBaseUrl'], result => {
      resolve((result.lexoraBaseUrl || DEFAULT_BASE_URL).replace(/\/$/, ''));
    });
  });
}

async function getSessionHeader(baseUrl) {
  return new Promise(resolve => {
    chrome.cookies.get({ url: baseUrl, name: 'session_id' }, cookie => {
      if (chrome.runtime.lastError || !cookie) { resolve({}); return; }
      resolve({ 'X-Lexora-Session-Id': cookie.value });
    });
  });
}

async function getContextSentence(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        if (typeof window.__lexoraCaptureSelection === 'function') {
          return window.__lexoraCaptureSelection();
        }
        return { word: '', context_sentence: '' };
      },
    });
    return results?.[0]?.result?.context_sentence || '';
  } catch {
    return '';
  }
}

function setBadge(tabId, text, color) {
  chrome.action.setBadgeText({ text, tabId });
  chrome.action.setBadgeBackgroundColor({ color, tabId });
  if (text && text !== '…') {
    setTimeout(() => chrome.action.setBadgeText({ text: '', tabId }), 3000);
  }
}

// ── Message handlers (from content scripts / overlay) ─────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  console.log('[Lexora BG] message received:', msg.action);
  if (msg.action === 'lexora-define') {
    handleDefine(msg).then(sendResponse).catch(() => sendResponse({ status: 'error' }));
  } else if (msg.action === 'lexora-add-word-overlay') {
    handleAddWordOverlay(msg).then(sendResponse).catch(() => sendResponse({ status: 'error' }));
  } else if (msg.action === 'lexora-get-daily-card') {
    handleDailyCard().then(sendResponse).catch(() => sendResponse({ status: 'error' }));
  } else if (msg.action === 'lexora-get-whoami') {
    handleWhoami().then(sendResponse).catch(() => sendResponse({ status: 'error' }));
  } else if (msg.action === 'lexora-get-learned-words') {
    handleGetLearnedWords().then(sendResponse).catch(() => sendResponse({ status: 'error' }));
  } else if (msg.action === 'lexora-explain-grammar') {
    handleExplainGrammar(msg).then(sendResponse).catch(() => sendResponse({ status: 'error' }));
  } else if (msg.action === 'lexora-writer-check') {
    handleWriterCheck(msg).then(sendResponse).catch(() => sendResponse({ status: 'error' }));
  } else if (msg.action === 'lexora-explain-slang') {
    handleExplainSlang(msg).then(sendResponse).catch(() => sendResponse({ status: 'error' }));
  } else if (msg.action === 'lexora-mic-start') {
    handleMicStart().then(sendResponse).catch((err) =>
      sendResponse({ status: 'error', message: String(err && err.message || err) }));
  } else if (msg.action === 'lexora-mic-stop') {
    handleMicStop().then(sendResponse).catch((err) =>
      sendResponse({ status: 'error', message: String(err && err.message || err) }));
  } else if (msg.action === 'lexora-mic-cancel') {
    handleMicCancel().then(sendResponse).catch((err) =>
      sendResponse({ status: 'error', message: String(err && err.message || err) }));
  } else if (msg.action === 'lexora-mic-ping') {
    // Diagnostic — used by the M33 DevTools sanity check. Returns
    // {status, recording, mime_type} without invoking the recorder.
    handleMicPing().then(sendResponse).catch((err) =>
      sendResponse({ status: 'error', message: String(err && err.message || err) }));
  } else if (msg.action === 'lexora-shadow-tts') {
    handleShadowTts(msg).then(sendResponse).catch((err) =>
      sendResponse({ status: 'error', message: String(err && err.message || err) }));
  } else if (msg.action === 'lexora-shadow-evaluate') {
    handleShadowEvaluate(msg).then(sendResponse).catch((err) =>
      sendResponse({ status: 'error', message: String(err && err.message || err) }));
  }
  return true; // MUST be at the very end — keeps channel open for all async handlers
});

async function handleDefine({ word, lang }) {
  // ── CANARY ── if this line never appears in the SW console, the message
  // never reached the background. Open chrome://extensions → Lexora → SW → Inspect.
  console.log('%c[Lexora BG] handleDefine CALLED', 'color:#4ade80;font-weight:bold', '— word:', word, '| lang:', lang);
  if (!word) return { status: 'error', message: 'word required' };

  const baseUrl = await getBaseUrl();
  console.log('[Lexora BG] baseUrl from storage:', baseUrl, '(must be http://localhost:5433 or your Lexora URL)');
  const sessionHeaders = await getSessionHeader(baseUrl);
  console.log('[Lexora BG] session headers:', sessionHeaders);

  const controller = new AbortController();
  const abortTimer = setTimeout(() => {
    console.error('[Lexora BG] FETCH TIMEOUT — aborting define request after 8s');
    controller.abort();
  }, 8000);

  try {
    // Using /define_v2 to bypass any Odoo bytecode cache of the old /define handler.
    // Both routes are registered on the same method; v2 forces a fresh route match.
    const finalUrl = `${baseUrl}/lexora_api/define_v2?word=${encodeURIComponent(word)}&lang=${encodeURIComponent(lang || 'en')}`;
    console.log('[Lexora BG] FETCHING URL:', finalUrl);
    const resp = await fetch(finalUrl, {
      method: 'GET',
      credentials: 'include',
      headers: sessionHeaders,
      signal: controller.signal,
    });
    clearTimeout(abortTimer);
    console.log('[Lexora BG] define HTTP status:', resp.status);
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    const data = await resp.json();
    console.log('[Lexora BG] define data — translations:', data.translations?.length ?? 0,
                '| live:', data.live ?? false,
                '| full:', data);
    if (data.live) {
      console.log('[Lexora BG] LIVE TRANSLATION active — results came from translation-service, not DB');
    }
    return data;
  } catch (err) {
    clearTimeout(abortTimer);
    console.error('[Lexora BG] FETCH FAILED:', err.name, err.message);
    return { status: 'error', message: err.message };
  }
}

async function handleAddWordOverlay({ word, source_language, source_url }) {
  if (!word) return { status: 'error', message: 'word required' };
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  const body = { word };
  if (source_language) body.source_language = source_language;
  if (source_url) body.source_url = source_url;
  try {
    const resp = await fetch(`${baseUrl}${ADD_WORD_PATH}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...sessionHeaders },
      body: JSON.stringify(body),
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    const data = await resp.json();
    if (data.status === 'ok') {
      // Invalidate the M27 word-list cache so the new word is highlighted on next page load
      chrome.storage.local.remove('lx_word_cache');
    }
    return data;
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

// ── New Tab handlers (M25) ─────────────────────────────────────────────────

async function handleDailyCard() {
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/daily_card`, {
      method: 'GET',
      credentials: 'include',
      headers: sessionHeaders,
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    return resp.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

async function handleWhoami() {
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/whoami`, {
      method: 'GET',
      credentials: 'include',
      headers: sessionHeaders,
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    return resp.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

// ── M27 — Learned word list (page highlighting) ───────────────────────────

async function handleGetLearnedWords() {
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/get_learned_words`, {
      method: 'GET',
      credentials: 'include',
      headers: sessionHeaders,
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    return resp.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

// ── M28 — Grammar Explainer ───────────────────────────────────────────────

async function handleExplainGrammar({ phrase, language }) {
  if (!phrase) return { status: 'error', message: 'phrase required' };
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/explain_grammar`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...sessionHeaders },
      body: JSON.stringify({ phrase, language: language || 'en' }),
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    return resp.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

// ── M32 — Slang & Idiom Explainer ─────────────────────────────────────────

async function handleExplainSlang({ phrase, source_language, native_language }) {
  if (!phrase) return { status: 'error', message: 'phrase required' };
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/explain_slang`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...sessionHeaders },
      body: JSON.stringify({
        phrase,
        source_language: source_language || 'en',
        native_language: native_language || 'en',
      }),
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    return resp.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

// ── M31 — Lexora Writer ───────────────────────────────────────────────────

async function handleWriterCheck({ text, language, context }) {
  if (!text || !text.trim()) return { status: 'error', message: 'text required' };
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  const body = { text, language: language || 'en' };
  if (context) body.context = context;
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/writer_check`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...sessionHeaders },
      body: JSON.stringify(body),
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    return resp.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

// ── M33 — Offscreen mic surface (Webpage Shadowing) ────────────────────────
//
// Recording happens in the chrome.offscreen document at offscreen.html
// (see ADR-032 / M33-S4). The user grants mic permission ONCE per
// extension; subsequent records on any tab reuse the grant.
//
// Routing:
//   content.js → chrome.runtime.sendMessage({action:'lexora-mic-start'})
//     → bg.js (this listener)
//     → ensureOffscreen() then chrome.runtime.sendMessage(
//         {target:'offscreen', action:'mic-start'})
//     → offscreen.js handles, sendResponse comes back here
//     → we forward the response to the originating content script's
//       sendResponse callback.
// ───────────────────────────────────────────────────────────────────────────

const _OFFSCREEN_URL = 'offscreen.html';

async function _ensureOffscreen() {
  if (!chrome.offscreen) {
    throw new Error('chrome.offscreen API not available — Chrome 116+ required');
  }
  // hasDocument throws on some Chromium builds when no offscreen doc has
  // ever been created — guard with try/catch and assume false.
  let exists = false;
  try {
    exists = await chrome.offscreen.hasDocument();
  } catch (err) {
    console.warn('[Lexora BG] chrome.offscreen.hasDocument threw:', err);
    exists = false;
  }
  if (exists) return;

  console.log('[Lexora BG] creating offscreen document for mic capture');
  await chrome.offscreen.createDocument({
    url:           _OFFSCREEN_URL,
    reasons:       ['USER_MEDIA'],
    justification: 'Record speech for pronunciation practice (Lexora M33 — Webpage Shadowing)',
  });
}

async function _sendToOffscreen(action) {
  // chrome.runtime.sendMessage with a Promise return form (MV3).
  return chrome.runtime.sendMessage({ target: 'offscreen', action });
}

async function handleMicStart() {
  await _ensureOffscreen();
  const resp = await _sendToOffscreen('mic-start');
  console.log('[Lexora BG] mic-start →', resp);
  return resp || { status: 'error', message: 'No response from offscreen.' };
}

async function handleMicStop() {
  if (!chrome.offscreen || !(await _hasOffscreenSafely())) {
    return { status: 'error', message: 'No active offscreen recorder.' };
  }
  const resp = await _sendToOffscreen('mic-stop');
  if (resp && resp.audio_b64) {
    console.log('[Lexora BG] mic-stop →',
      'mime=' + resp.mime_type,
      'duration_ms=' + resp.duration_ms,
      'size_bytes=' + resp.size_bytes);
  } else {
    console.log('[Lexora BG] mic-stop →', resp);
  }
  return resp || { status: 'error', message: 'No response from offscreen.' };
}

async function handleMicCancel() {
  if (!chrome.offscreen || !(await _hasOffscreenSafely())) {
    return { status: 'ok' };  // nothing to cancel
  }
  return await _sendToOffscreen('mic-cancel');
}

async function handleMicPing() {
  // Diagnostic — surfaces the offscreen doc's recording state without
  // invoking getUserMedia. Useful for debugging routing without burning
  // a permission prompt.
  if (!chrome.offscreen) {
    return { status: 'error', message: 'chrome.offscreen API unavailable.' };
  }
  if (!(await _hasOffscreenSafely())) {
    return { status: 'ok', offscreen: false, recording: false };
  }
  const resp = await _sendToOffscreen('ping');
  return { status: 'ok', offscreen: true, ...(resp || {}) };
}

async function _hasOffscreenSafely() {
  try {
    return await chrome.offscreen.hasDocument();
  } catch {
    return false;
  }
}

// ── M33 — Webpage Shadowing proxy handlers ────────────────────────────────
//
// content.js / overlay.js can't talk to the Odoo proxy directly because
// SameSite cookie rules block third-party requests; the same X-Lexora-
// Session-Id bridge used by every other M22+ handler applies. These two
// handlers run in the service worker and forward to the Odoo proxies
// added in M33-S3.

// _b64ToBytes — base64 string → Uint8Array. Used to reconstruct the
// recorded audio Blob in the service worker before forwarding as
// multipart to the Odoo proxy.
function _b64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// _bytesToB64 — Uint8Array → base64 string. Used to ferry binary audio
// bytes back to the content script (chrome.runtime.sendMessage can only
// carry JSON-serialisable values, so we base64 the audio for transport).
function _bytesToB64(bytes) {
  // chunked btoa to avoid stack overflow on large buffers
  let bin = '';
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

async function handleShadowTts({ text, language }) {
  if (!text || !text.trim()) {
    return { status: 'error', message: 'text required' };
  }
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/shadow_tts`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...sessionHeaders },
      body: JSON.stringify({ text, language: language || 'en' }),
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) {
      let detail = '';
      try { detail = JSON.stringify(await resp.json()); } catch { detail = resp.statusText; }
      return { status: 'error', message: `HTTP ${resp.status}: ${detail}` };
    }
    const buf = await resp.arrayBuffer();
    const audio_b64 = _bytesToB64(new Uint8Array(buf));
    const mime_type = resp.headers.get('Content-Type') || 'audio/mpeg';
    return { status: 'ok', audio_b64, mime_type, size_bytes: buf.byteLength };
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

async function handleShadowEvaluate({ audio_b64, mime_type, reference_text, language }) {
  if (!audio_b64) return { status: 'error', message: 'audio_b64 required' };
  if (!reference_text) return { status: 'error', message: 'reference_text required' };
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);

  try {
    const bytes = _b64ToBytes(audio_b64);
    const blob  = new Blob([bytes], { type: mime_type || 'audio/webm' });
    const fd = new FormData();
    fd.append('audio', blob, 'recording' + (mime_type === 'audio/webm;codecs=opus' ? '.webm' : '.bin'));
    fd.append('reference_text', reference_text);
    fd.append('language', language || 'en');

    const resp = await fetch(`${baseUrl}/lexora_api/shadow_evaluate`, {
      method: 'POST',
      credentials: 'include',
      headers: { ...sessionHeaders }, // do NOT set Content-Type — let the
                                       // browser set the multipart boundary
      body: fd,
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) {
      let detail;
      try { detail = await resp.json(); } catch { detail = { detail: resp.statusText }; }
      return { status: 'error', http_status: resp.status, ...detail };
    }
    return await resp.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

// ── Context menu registration ──────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'add-to-lexora',
    title: 'Add to Lexora',
    contexts: ['selection'],
  });
});

// ── Context menu click handler ─────────────────────────────────────────────

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== 'add-to-lexora') return;

  const word = (info.selectionText || '').trim();
  if (!word) return;

  setBadge(tab.id, '…', '#6366f1');

  // Get surrounding sentence from the content script
  const contextSentence = tab?.id ? await getContextSentence(tab.id) : '';

  // Store for popup pre-fill (popup checks timestamp, ignores if >30s old)
  try {
    await chrome.storage.session.set({
      lexoraPendingCapture: { word, context_sentence: contextSentence, ts: Date.now() },
    });
  } catch {
    // chrome.storage.session unavailable in older Chrome — non-fatal
  }

  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);

  const body = { word, source_url: tab?.url || undefined };
  if (contextSentence) body.context_sentence = contextSentence;
  Object.keys(body).forEach(k => body[k] === undefined && delete body[k]);

  try {
    const resp = await fetch(`${baseUrl}${ADD_WORD_PATH}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...sessionHeaders },
      body: JSON.stringify(body),
    });

    if (resp.status === 401) {
      setBadge(tab.id, '!', '#ef4444');
      chrome.tabs.sendMessage(tab.id, { action: 'show-toast', status: 'unauthorized', word });
      return;
    }

    const data = await resp.json();
    if (data.status === 'ok') {
      // Invalidate M27 word-list cache so the new word highlights on next page scan
      chrome.storage.local.remove('lx_word_cache');
      setBadge(tab.id, '✓', '#22c55e');
      chrome.tabs.sendMessage(tab.id, { action: 'show-toast', status: 'ok', word });
    } else if (data.status === 'duplicate') {
      setBadge(tab.id, '=', '#f59e0b');
      chrome.tabs.sendMessage(tab.id, { action: 'show-toast', status: 'duplicate', word });
    } else {
      setBadge(tab.id, '!', '#ef4444');
      chrome.tabs.sendMessage(tab.id, { action: 'show-toast', status: 'error', word });
    }
  } catch {
    setBadge(tab.id, '!', '#ef4444');
    chrome.tabs.sendMessage(tab.id, { action: 'show-toast', status: 'error', word }).catch(() => {});
  }
});
