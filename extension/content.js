'use strict';

// ---------------------------------------------------------------------------
// Lexora content script — M23 Contextual Capture
// Listens for {action:"capture"} from the popup (via chrome.scripting) and
// returns {word, context_sentence} based on the current text selection.
// ---------------------------------------------------------------------------

function getSurroundingSentence(selectedText) {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return '';

  const range = sel.getRangeAt(0);
  const container = range.startContainer;

  // Walk up to the nearest block-level text container
  let node = container.nodeType === Node.TEXT_NODE ? container : container.firstChild;
  let fullText = '';

  if (node && node.parentElement) {
    // Get the full text of the containing block element
    let block = node.parentElement;
    while (block && !isBlockElement(block)) {
      block = block.parentElement;
    }
    fullText = block ? (block.textContent || '') : (node.parentElement.textContent || '');
  }

  if (!fullText) return '';

  // Split on sentence-ending punctuation and find the sentence containing selectedText
  const sentences = fullText.split(/(?<=[.!?])\s+/);
  const lower = selectedText.toLowerCase();
  for (const s of sentences) {
    if (s.toLowerCase().includes(lower)) {
      const trimmed = s.trim();
      if (trimmed.length <= 500) return trimmed;
      // If sentence is too long, return a 300-char window around the selection
      const idx = trimmed.toLowerCase().indexOf(lower);
      const start = Math.max(0, idx - 100);
      const end = Math.min(trimmed.length, idx + lower.length + 200);
      return trimmed.slice(start, end).trim();
    }
  }
  return '';
}

function isBlockElement(el) {
  const blocks = new Set(['P','DIV','LI','TD','TH','H1','H2','H3','H4','H5','H6',
    'BLOCKQUOTE','ARTICLE','SECTION','MAIN','ASIDE','FIGCAPTION','CAPTION']);
  return blocks.has(el.tagName);
}

// Expose as a function that can be called via chrome.scripting.executeScript
function captureSelection() {
  const word = window.getSelection()?.toString().trim() || '';
  if (!word) return { word: '', context_sentence: '' };
  const context_sentence = getSurroundingSentence(word);
  return { word, context_sentence };
}

// Make captureSelection available in the page's global scope for executeScript
window.__lexoraCaptureSelection = captureSelection;
