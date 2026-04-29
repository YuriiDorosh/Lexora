'use strict';

const DEFAULT_BASE_URL = 'http://localhost:5433';
const ADD_WORD_PATH = '/lexora_api/add_word';

const $ = id => document.getElementById(id);

async function getBaseUrl() {
  return new Promise(resolve => {
    chrome.storage.sync.get(['lexoraBaseUrl'], result => {
      resolve((result.lexoraBaseUrl || DEFAULT_BASE_URL).replace(/\/$/, ''));
    });
  });
}

// ---------------------------------------------------------------------------
// Session bridge: Chrome blocks SameSite=Lax cookies on cross-origin fetches
// from extension → HTTP localhost.  We read the cookie explicitly via the
// chrome.cookies API (requires "cookies" permission + host_permissions) and
// forward it as a custom header X-Lexora-Session-Id.  Odoo reads that header
// and loads the session from its store, bypassing the SameSite restriction.
// ---------------------------------------------------------------------------
async function getSessionHeader(baseUrl) {
  return new Promise(resolve => {
    // chrome.cookies.get needs the exact URL and cookie name
    chrome.cookies.get({ url: baseUrl, name: 'session_id' }, cookie => {
      if (chrome.runtime.lastError || !cookie) {
        resolve({});
        return;
      }
      resolve({ 'X-Lexora-Session-Id': cookie.value });
    });
  });
}

async function checkLoggedIn(baseUrl) {
  try {
    const sessionHeaders = await getSessionHeader(baseUrl);
    const resp = await fetch(`${baseUrl}/lexora_api/whoami`, {
      method: 'GET',
      credentials: 'include',
      headers: sessionHeaders,
    });
    if (resp.status === 401) return false;
    if (!resp.ok) return false;
    const ct = resp.headers.get('Content-Type') || '';
    if (!ct.includes('application/json')) return false;
    const data = await resp.json();
    return data.status === 'ok';
  } catch {
    return false;
  }
}

async function prefillFromSelection() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return;

    // Try the rich capture function injected by content.js first
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        if (typeof window.__lexoraCaptureSelection === 'function') {
          return window.__lexoraCaptureSelection();
        }
        // Fallback: plain selection only
        return { word: window.getSelection()?.toString().trim() || '', context_sentence: '' };
      },
    });

    const captured = results?.[0]?.result || {};
    const word = (captured.word || '').trim();
    const ctx = (captured.context_sentence || '').trim();

    if (word && word.length <= 500) {
      $('lx-word').value = word;
    }
    if (ctx && ctx.length <= 500) {
      $('lx-context').value = ctx;
    }
  } catch {
    // Denied on chrome:// pages — silently ignore
  }
}

async function getPageUrl() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return tab?.url || '';
  } catch {
    return '';
  }
}

function setStatus(msg, cls) {
  const el = $('lx-status');
  el.textContent = msg;
  el.className = `lx-status ${cls}`;
}

async function init() {
  const baseUrl = await getBaseUrl();
  const loggedIn = await checkLoggedIn(baseUrl);

  if (!loggedIn) {
    $('lx-form-wrap').style.display = 'none';
    $('lx-not-logged-in').style.display = 'block';
    const linkWrap = $('lx-login-link-wrap');
    linkWrap.innerHTML = `<a href="${baseUrl}/web/login" target="_blank">Log in to Lexora →</a>`;

    // Surface the localhost vs 127.0.0.1 tip
    const tip = document.getElementById('lx-url-tip');
    if (tip) tip.style.display = 'block';
    return;
  }

  await prefillFromSelection();

  $('lx-save-btn').addEventListener('click', async () => {
    const word = $('lx-word').value.trim();
    if (!word) {
      setStatus('Please enter a word or phrase.', 'err');
      $('lx-word').focus();
      return;
    }

    const btn = $('lx-save-btn');
    btn.disabled = true;
    setStatus('Saving…', 'info');

    const body = {
      word,
      source_language: $('lx-lang').value || undefined,
      translation: $('lx-translation').value.trim() || undefined,
      context_sentence: $('lx-context').value.trim() || undefined,
      source_url: await getPageUrl() || undefined,
    };

    Object.keys(body).forEach(k => body[k] === undefined && delete body[k]);

    const sessionHeaders = await getSessionHeader(baseUrl);

    try {
      const resp = await fetch(`${baseUrl}${ADD_WORD_PATH}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...sessionHeaders },
        body: JSON.stringify(body),
      });

      if (resp.status === 401) {
        setStatus('Session expired. Please log in to Lexora.', 'err');
        btn.disabled = false;
        return;
      }

      const data = await resp.json();

      if (data.status === 'ok') {
        setStatus('✓ Saved to your vocabulary!', 'ok');
        setTimeout(() => window.close(), 1200);
      } else if (data.status === 'duplicate') {
        setStatus('Already in your vocabulary.', 'dup');
        btn.disabled = false;
      } else {
        setStatus(data.message || 'Unexpected error.', 'err');
        btn.disabled = false;
      }
    } catch (err) {
      setStatus(`Connection error: ${err.message}`, 'err');
      btn.disabled = false;
    }
  });
}

$('lx-open-options').addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
});

// Tip link inside "not logged in" panel
document.addEventListener('click', e => {
  if (e.target && e.target.id === 'lx-tip-open-opts') {
    chrome.runtime.openOptionsPage();
  }
});

init();
