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
    const finalUrl = `${baseUrl}/lexora_api/define?word=${encodeURIComponent(word)}&lang=${encodeURIComponent(lang || 'en')}`;
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
    console.log('[Lexora BG] define data:', data);
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
