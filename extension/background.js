'use strict';
// Lexora service worker — MV3 background script.
// Currently a stub; M23 will add context-menu registration and badge updates.

chrome.runtime.onInstalled.addListener(() => {
  console.debug('[Lexora] extension installed / updated');
});
