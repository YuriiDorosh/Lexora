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
  // whoami returns 200 JSON on valid session, 401 JSON when not logged in.
  // auth='none' on the route prevents Odoo from issuing a 303 redirect that
  // would load the HTML login page inside the popup.
  try {
    const resp = await fetch(`${baseUrl}/lexora_api/whoami`, {
      method: 'GET',
      credentials: 'include',
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

init();
