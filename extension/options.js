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
});
