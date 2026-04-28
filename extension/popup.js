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

async function checkLoggedIn(baseUrl) {
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/add_word`, {
      method: 'OPTIONS',
      credentials: 'include',
    });
    // If OPTIONS succeeds at all (204 or any 2xx/3xx), the server is reachable.
    // We confirm auth by sending a GET to /web/session/get_session_info style check
    // instead, use a HEAD to a known auth-required route.
    const check = await fetch(`${baseUrl}/my/vocabulary`, {
      method: 'HEAD',
      credentials: 'include',
      redirect: 'manual',
    });
    // If redirected to /web/login, user is not authenticated
    if (check.type === 'opaqueredirect' || check.status === 0) return false;
    if (check.status >= 300 && check.status < 400) return false;
    return check.ok || check.status === 200 || check.status === 404;
  } catch {
    return false;
  }
}

async function prefillFromSelection() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return;
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection()?.toString().trim() || '',
    });
    const sel = results?.[0]?.result || '';
    if (sel && sel.length <= 500) {
      $('lx-word').value = sel;
    }
  } catch {
    // scripting may be denied on chrome:// pages — silently ignore
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

    // Remove undefined keys
    Object.keys(body).forEach(k => body[k] === undefined && delete body[k]);

    try {
      const resp = await fetch(`${baseUrl}${ADD_WORD_PATH}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      // If we got redirected to login page (fetch follows redirects — check URL)
      if (!resp.ok && resp.status === 0) {
        setStatus('Not logged in. Please log in to Lexora first.', 'err');
        btn.disabled = false;
        return;
      }

      // Odoo returns 303 on auth failure; fetch follows it but lands on HTML
      const ct = resp.headers.get('Content-Type') || '';
      if (!ct.includes('application/json')) {
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

init();
