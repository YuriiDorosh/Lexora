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
  if (msg.action === 'lexora-define') {
    handleDefine(msg).then(sendResponse).catch(() => sendResponse({ status: 'error' }));
    return true; // keep channel open for async response
  }
  if (msg.action === 'lexora-add-word-overlay') {
    handleAddWordOverlay(msg).then(sendResponse).catch(() => sendResponse({ status: 'error' }));
    return true;
  }
});

async function handleDefine({ word, lang }) {
  if (!word) return { status: 'error', message: 'word required' };
  const baseUrl = await getBaseUrl();
  const sessionHeaders = await getSessionHeader(baseUrl);
  try {
    const url = `${baseUrl}/lexora_api/define?word=${encodeURIComponent(word)}&lang=${encodeURIComponent(lang || 'en')}`;
    const resp = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: sessionHeaders,
    });
    if (resp.status === 401) return { status: 'unauthorized' };
    if (!resp.ok) return { status: 'error', message: `HTTP ${resp.status}` };
    return await resp.json();
  } catch (err) {
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
