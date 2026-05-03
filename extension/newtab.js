'use strict';

// ---------------------------------------------------------------------------
// Lexora New Tab — M25
//
// Displays a premium new-tab page with:
//   - Live clock + personalised greeting
//   - Daily word card (random vocabulary entry with translations)
//   - Idiom card fallback when vocabulary is empty
//   - Refresh and Practice CTAs
// ---------------------------------------------------------------------------

const DEFAULT_BASE_URL = 'http://localhost:5433';

const LANG_FLAGS = { en: '🇬🇧', uk: '🇺🇦', el: '🇬🇷', pl: '🇵🇱' };
const LANG_NAMES = { en: 'English', uk: 'Ukrainian', el: 'Greek', pl: 'Polish' };

// ── Helpers ────────────────────────────────────────────────────────────────

async function getBaseUrl() {
  return new Promise(resolve => {
    chrome.storage.sync.get(['lexoraBaseUrl'], r => {
      resolve((r.lexoraBaseUrl || DEFAULT_BASE_URL).replace(/\/$/, ''));
    });
  });
}

/**
 * Send a message to the background service worker and wait for a response.
 * All network calls go through the background so the session cookie is
 * attached correctly (the new-tab page is an extension page and cannot
 * read or send the Lexora session cookie directly).
 *
 * Includes a 5-second failsafe timeout so a dead SW never hangs the page.
 */
function sendToBg(action, payload = {}, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Background response timed out for action: ${action}`));
    }, timeoutMs);

    chrome.runtime.sendMessage({ action, ...payload }, response => {
      clearTimeout(timer);
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response || { status: 'error', message: 'No response from background' });
    });
  });
}

// ── Clock ──────────────────────────────────────────────────────────────────

function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  document.getElementById('lxClock').textContent = `${h}:${m}`;
}

function updateGreeting(userName) {
  const h = new Date().getHours();
  const period = h < 12 ? 'morning' : h < 18 ? 'afternoon' : 'evening';
  const name = userName ? `, ${userName.split(' ')[0]}` : '';
  document.getElementById('lxGreeting').textContent = `Good ${period}${name}`;
}

// ── State helpers ─────────────────────────────────────────────────────────

const STATES = ['lxStateLoading', 'lxStateWord', 'lxStateIdiom', 'lxStateUnauth', 'lxStateEmpty'];

function showState(id) {
  STATES.forEach(s => {
    const el = document.getElementById(s);
    if (el) el.style.display = (s === id) ? 'flex' : 'none';
  });
}

function showToast(msg, durationMs = 2800) {
  const el = document.getElementById('lxToast');
  el.textContent = msg;
  el.style.display = 'block';
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.style.display = 'none'; }, durationMs);
}

// ── Render vocabulary word ─────────────────────────────────────────────────

function renderWordCard(data, baseUrl) {
  // eyebrow
  document.getElementById('lxCardEyebrow').textContent =
    data.type === 'vocabulary' ? 'Word of the moment' : 'Daily word';

  // word + lang pill
  document.getElementById('lxWord').textContent = data.word || data.source_text || '';
  const langCode = (data.source_language || 'en').toLowerCase();
  document.getElementById('lxLangPill').textContent =
    (LANG_FLAGS[langCode] || '') + ' ' + (LANG_NAMES[langCode] || langCode.toUpperCase());

  // translations
  const trContainer = document.getElementById('lxTranslations');
  trContainer.innerHTML = '';
  const translations = data.translations || [];
  if (translations.length) {
    translations.forEach(tr => {
      const tl = (tr.target_language || '').toLowerCase();
      const row = document.createElement('div');
      row.className = 'lx-translation-row';
      row.innerHTML = `
        <span class="lx-tr-flag">${LANG_FLAGS[tl] || '🌐'}</span>
        <span class="lx-tr-lang">${tl.toUpperCase()}</span>
        <span class="lx-tr-text">${escHtml(tr.translated_text || '')}</span>
      `;
      trContainer.appendChild(row);
    });
  } else {
    const none = document.createElement('p');
    none.style.cssText = 'font-size:13px;color:var(--lx-muted);margin-bottom:8px';
    none.textContent = 'No translations yet — click Practice to add them.';
    trContainer.appendChild(none);
  }

  // example
  const exBox = document.getElementById('lxExample');
  if (data.example_sentence) {
    document.getElementById('lxExampleText').textContent = data.example_sentence;
    exBox.style.display = 'flex';
  } else {
    exBox.style.display = 'none';
  }

  // practice button
  const practiceBtn = document.getElementById('lxPracticeBtn');
  practiceBtn.href = `${baseUrl}/my/practice`;
  practiceBtn.target = '_blank';

  showState('lxStateWord');
}

// ── Render idiom ───────────────────────────────────────────────────────────

function renderIdiomCard(data) {
  const langCode = (data.language || 'en').toLowerCase();
  const badge = document.getElementById('lxIdiomLangBadge');
  badge.className = 'lx-idiom-lang';
  badge.textContent = (LANG_FLAGS[langCode] || '') + ' ' + langCode.toUpperCase();

  document.getElementById('lxIdiomExpr').textContent = data.expression || '';
  document.getElementById('lxIdiomLiteral').textContent = data.literal_meaning || '—';
  document.getElementById('lxIdiomMeaning').textContent = data.idiomatic_meaning || '—';

  const exBox = document.getElementById('lxIdiomExample');
  if (data.example_sentence) {
    document.getElementById('lxIdiomExampleText').textContent = data.example_sentence;
    exBox.style.display = 'flex';
  } else {
    exBox.style.display = 'none';
  }

  showState('lxStateIdiom');
}

// ── Fetch & display daily card ─────────────────────────────────────────────

let _currentIdiomData = null;
let _savedIdiom = false;

async function loadDailyCard(baseUrl) {
  showState('lxStateLoading');
  _savedIdiom = false;
  document.getElementById('lxCard').classList.remove('lx-saved-flash');

  try {
    const data = await sendToBg('lexora-get-daily-card');

    if (data.status === 'unauthorized') {
      const signinBtn = document.getElementById('lxSigninBtn');
      signinBtn.href = `${baseUrl}/web/login`;
      signinBtn.target = '_blank';
      showState('lxStateUnauth');
      return;
    }

    if (data.type === 'vocabulary' || data.type === 'word') {
      renderWordCard(data, baseUrl);
    } else if (data.type === 'idiom') {
      _currentIdiomData = data;
      renderIdiomCard(data);
    } else {
      // No vocabulary and no idioms — prompt to add words
      const addBtn = document.getElementById('lxAddWordsBtn');
      addBtn.href = `${baseUrl}/my/vocabulary/new`;
      addBtn.target = '_blank';
      showState('lxStateEmpty');
    }
  } catch (err) {
    console.error('[Lexora NT] daily_card error:', err);
    const signinBtn = document.getElementById('lxSigninBtn');
    signinBtn.href = `${baseUrl}/web/login`;
    signinBtn.target = '_blank';
    showState('lxStateUnauth');
  }
}

// ── Save idiom to vocabulary ───────────────────────────────────────────────

async function saveIdiom(data) {
  if (_savedIdiom) { showToast('Already saved ✓'); return; }
  const btn = document.getElementById('lxSaveIdiomBtn');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    const result = await sendToBg('lexora-add-word-overlay', {
      word: data.expression,
      source_language: data.language || 'en',
    });
    if (result.status === 'ok') {
      _savedIdiom = true;
      btn.textContent = '✓ Saved';
      document.getElementById('lxCard').classList.add('lx-saved-flash');
      showToast('Added to your vocabulary ✓');
    } else if (result.status === 'duplicate') {
      _savedIdiom = true;
      btn.textContent = '= Already in list';
      showToast('Already in your vocabulary');
    } else if (result.status === 'unauthorized') {
      showToast('Please sign in to Lexora first');
      btn.textContent = 'Save to vocabulary';
      btn.disabled = false;
    } else {
      throw new Error(result.message || 'Unknown error');
    }
  } catch (err) {
    console.error('[Lexora NT] save idiom error:', err);
    showToast('Could not save — try again');
    btn.textContent = 'Save to vocabulary';
    btn.disabled = false;
  }
}

// ── Utility ────────────────────────────────────────────────────────────────

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function setRefreshSpinning(btnId, spinning) {
  const btn = document.getElementById(btnId);
  if (spinning) btn.classList.add('lx-btn-spinning');
  else btn.classList.remove('lx-btn-spinning');
  btn.disabled = spinning;
}

// ── Check who is logged in (for greeting) ─────────────────────────────────

async function loadUserGreeting() {
  try {
    const data = await sendToBg('lexora-get-whoami');
    if (data && data.status === 'ok' && data.name) {
      updateGreeting(data.name);
      document.getElementById('lxNav').style.display = 'flex';
    } else {
      updateGreeting('');
    }
  } catch {
    updateGreeting('');
  }
}

// ── Wire up nav links ──────────────────────────────────────────────────────

function wireNavLinks(baseUrl) {
  const vocab = document.getElementById('lxVocabLink');
  const practice = document.getElementById('lxPracticeLink');
  vocab.href = `${baseUrl}/my/vocabulary`;
  vocab.target = '_blank';
  practice.href = `${baseUrl}/my/practice`;
  practice.target = '_blank';
}

// ── Disable new tab override ───────────────────────────────────────────────

document.getElementById('lxDisableBtn').addEventListener('click', () => {
  if (confirm('Restore the default new tab page? (You can re-enable Lexora from the extension options.)')) {
    chrome.storage.sync.set({ lexoraNewTabDisabled: true }, () => {
      chrome.tabs.create({ url: 'chrome-search://local-ntp/local-ntp.html' });
    });
  }
});

// ── Init ───────────────────────────────────────────────────────────────────

(async function init() {
  // Clock ticks every second
  updateClock();
  setInterval(updateClock, 1000);

  const baseUrl = await getBaseUrl();
  wireNavLinks(baseUrl);

  // Load greeting and daily card in parallel
  await Promise.all([
    loadUserGreeting(),
    loadDailyCard(baseUrl),
  ]);

  // Refresh buttons
  document.getElementById('lxRefreshBtn').addEventListener('click', async () => {
    setRefreshSpinning('lxRefreshBtn', true);
    await loadDailyCard(baseUrl);
    setRefreshSpinning('lxRefreshBtn', false);
  });

  document.getElementById('lxRefreshIdiomsBtn').addEventListener('click', async () => {
    setRefreshSpinning('lxRefreshIdiomsBtn', true);
    await loadDailyCard(baseUrl);
    setRefreshSpinning('lxRefreshIdiomsBtn', false);
  });

  // Save idiom button
  document.getElementById('lxSaveIdiomBtn').addEventListener('click', () => {
    if (_currentIdiomData) saveIdiom(_currentIdiomData);
  });
})();
