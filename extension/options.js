'use strict';

const DEFAULT_BASE_URL = 'http://localhost:5433';

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('lx-base-url');
  const btn = document.getElementById('lx-save-btn');
  const savedMsg = document.getElementById('lx-saved');

  chrome.storage.sync.get(['lexoraBaseUrl'], result => {
    input.value = result.lexoraBaseUrl || DEFAULT_BASE_URL;
  });

  btn.addEventListener('click', () => {
    const url = (input.value || DEFAULT_BASE_URL).replace(/\/$/, '');
    chrome.storage.sync.set({ lexoraBaseUrl: url }, () => {
      savedMsg.style.display = 'inline';
      setTimeout(() => { savedMsg.style.display = 'none'; }, 2000);
    });
  });
});
