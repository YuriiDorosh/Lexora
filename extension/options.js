'use strict';

const DEFAULT_BASE_URL = 'http://localhost:5433';

document.addEventListener('DOMContentLoaded', () => {
  const input    = document.getElementById('lx-base-url');
  const btn      = document.getElementById('lx-save-btn');
  const savedMsg = document.getElementById('lx-saved');
  const writerEl = document.getElementById('lx-writer-enabled');
  const nativeEl = document.getElementById('lexora_native_language');

  // ── Initial load ────────────────────────────────────────────────────────
  // lexora_writer_enabled is the M31 feature toggle, default ON when the
  // key is absent (matches the content.js bootstrap logic — undefined !==
  // false, so the FAB shows by default for first-time users).
  // lexora_native_language is the M32 explanation-language picker; default
  // 'en' when the key is absent.
  chrome.storage.sync.get(
    ['lexoraBaseUrl', 'lexora_writer_enabled', 'lexora_native_language'],
    result => {
      input.value = result.lexoraBaseUrl || DEFAULT_BASE_URL;
      if (writerEl) {
        writerEl.checked = result.lexora_writer_enabled !== false;
      }
      if (nativeEl) {
        nativeEl.value = result.lexora_native_language || 'en';
      }
    },
  );

  // ── Save server URL ─────────────────────────────────────────────────────
  btn.addEventListener('click', () => {
    const url = (input.value || DEFAULT_BASE_URL).replace(/\/$/, '');
    chrome.storage.sync.set({ lexoraBaseUrl: url }, () => {
      savedMsg.style.display = 'inline';
      setTimeout(() => { savedMsg.style.display = 'none'; }, 2000);
    });
  });

  // ── M31: Writer toggle (autosave, no Save button needed) ───────────────
  // content.js subscribes to chrome.storage.onChanged for this key, so the
  // FAB hides/shows live across all open tabs without a refresh.
  if (writerEl) {
    writerEl.addEventListener('change', () => {
      chrome.storage.sync.set({ lexora_writer_enabled: writerEl.checked });
    });
  }

  // ── M32: Explanation-language picker (autosave) ────────────────────────
  // content.js + overlay.js read this on every "Explain Slang/Idiom" click,
  // so a change here takes effect on the next button press — no refresh.
  if (nativeEl) {
    nativeEl.addEventListener('change', () => {
      chrome.storage.sync.set({ lexora_native_language: nativeEl.value });
    });
  }

  // ── M33: Mic-permission grant ──────────────────────────────────────────
  // The Options page lives at chrome-extension://<id>/options.html — the
  // SAME origin as offscreen.html. Granting mic permission here teaches
  // Chrome to allow getUserMedia for the entire extension, which the
  // offscreen recorder will inherit on its next call.
  //
  // Flow:
  //   1. Click → navigator.mediaDevices.getUserMedia({audio:true})
  //   2. Permission prompt appears (or grants instantly if already
  //      decided)
  //   3. Stream resolves → immediately stop every track (we don't actually
  //      want to record here, just register the grant)
  //   4. Show "Permission granted!" — user can close the tab and the
  //      grant persists for the offscreen doc.
  // On NotAllowedError we hint at chrome://extensions site-permission
  // reset because once Chrome has hard-denied a permission, granting
  // again requires resetting it manually.
  const micGrantBtn = document.getElementById('lx-mic-grant-btn');
  const micStatus   = document.getElementById('lx-mic-status');

  function _escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _setMicStatus(kind, html) {
    if (!micStatus) return;
    micStatus.className = 'lx-mic-status ' + kind;
    micStatus.innerHTML = html;
  }

  if (micGrantBtn) {
    micGrantBtn.addEventListener('click', async () => {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        _setMicStatus('error',
          'This browser does not expose <code>navigator.mediaDevices</code>. ' +
          'Use Chrome 116+ or Edge.');
        return;
      }

      micGrantBtn.disabled = true;
      _setMicStatus('busy', 'Requesting microphone permission…');

      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (err) {
        micGrantBtn.disabled = false;
        const name = (err && err.name) || 'Error';
        if (name === 'NotAllowedError') {
          _setMicStatus('error',
            '🚫 Permission denied. To re-enable: open ' +
            '<code>chrome://extensions</code>, click <strong>Details</strong> ' +
            'on Lexora, then under <strong>Site access / Site permissions</strong> ' +
            'reset the microphone setting and click this button again.');
        } else if (name === 'NotFoundError' || name === 'OverconstrainedError') {
          _setMicStatus('error',
            '🎤 No microphone detected. Plug in a mic, then click again.');
        } else {
          _setMicStatus('error',
            '⚠️ <code>' + _escHtml(name) + '</code>: ' +
            _escHtml((err && err.message) || 'permission request failed'));
        }
        return;
      }

      // Release the tracks immediately — we wanted the GRANT, not the
      // stream. The grant persists for chrome-extension://<id>/* origin
      // so the offscreen.js getUserMedia call inherits it.
      try {
        stream.getTracks().forEach((t) => {
          try { t.stop(); } catch { /* ignore */ }
        });
      } catch { /* ignore */ }

      micGrantBtn.disabled = false;
      _setMicStatus('ok',
        '✓ Permission granted! You can now use ' +
        '<strong>🎤 Practice Pronunciation</strong> on any webpage. ' +
        'No further prompts will appear.');
    });
  }
});
