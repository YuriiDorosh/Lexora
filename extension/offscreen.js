'use strict';

// ---------------------------------------------------------------------------
// Lexora offscreen mic recorder — M33-S4
// ---------------------------------------------------------------------------
//
// Runs inside the chrome.offscreen document at
// chrome-extension://<id>/offscreen.html. Hosts getUserMedia +
// MediaRecorder on the extension's origin so the user grants mic
// permission ONCE per extension.
//
// Communication: service worker (background.js) → chrome.runtime.sendMessage
// with {target:'offscreen', action:'mic-start' | 'mic-stop' | 'mic-cancel'}.
// We reply via sendResponse with the base64 audio + metadata when done.
// ---------------------------------------------------------------------------

let _recorder  = null;
let _stream    = null;
let _chunks    = [];
let _mimeType  = '';
let _startedAt = 0;

const _MIME_PREFERENCE = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
];

function _pickMimeType() {
  if (typeof MediaRecorder === 'undefined') return '';
  for (const m of _MIME_PREFERENCE) {
    try {
      if (MediaRecorder.isTypeSupported(m)) return m;
    } catch { /* ignore */ }
  }
  return '';
}

function _cleanup() {
  if (_stream) {
    _stream.getTracks().forEach((t) => {
      try { t.stop(); } catch { /* ignore */ }
    });
    _stream = null;
  }
  _recorder = null;
  _chunks   = [];
}

async function startRecording() {
  if (_recorder && _recorder.state !== 'inactive') {
    return { status: 'error', message: 'A recording is already in progress.' };
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return { status: 'error', message: 'getUserMedia is not available in this offscreen context.' };
  }

  // Permission UI fires here on first call per extension install. The
  // browser remembers the grant for chrome-extension://<id>; subsequent
  // calls reuse it without prompting.
  try {
    _stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    return {
      status: 'error',
      message: err && err.name === 'NotAllowedError'
        ? 'Microphone permission denied. Open the extension Options page to retry.'
        : `getUserMedia failed: ${err && err.message || String(err)}`,
    };
  }

  _mimeType = _pickMimeType();
  try {
    _recorder = _mimeType
      ? new MediaRecorder(_stream, { mimeType: _mimeType })
      : new MediaRecorder(_stream);
    _mimeType = _recorder.mimeType || _mimeType || 'audio/webm';
  } catch (err) {
    _cleanup();
    return { status: 'error', message: `MediaRecorder construction failed: ${err && err.message || String(err)}` };
  }

  _chunks = [];
  _recorder.ondataavailable = (e) => {
    if (e && e.data && e.data.size > 0) _chunks.push(e.data);
  };

  try {
    _recorder.start();
    _startedAt = Date.now();
  } catch (err) {
    _cleanup();
    return { status: 'error', message: `MediaRecorder.start() failed: ${err && err.message || String(err)}` };
  }

  return { status: 'ok', mime_type: _mimeType };
}

function stopRecording() {
  return new Promise((resolve) => {
    if (!_recorder || _recorder.state === 'inactive') {
      resolve({ status: 'error', message: 'No active recording to stop.' });
      return;
    }

    _recorder.onstop = () => {
      const mime = _mimeType || 'audio/webm';
      const blob = new Blob(_chunks, { type: mime });
      const duration_ms = Date.now() - _startedAt;
      const size = blob.size;

      // Convert blob → base64 via FileReader. The data-URL prefix
      // ("data:audio/webm;base64,") is stripped before returning so the
      // caller gets pure base64 they can re-construct a Blob from.
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = String(reader.result || '');
        const audio_b64 = dataUrl.split(',', 2)[1] || '';
        _cleanup();
        resolve({
          status:      'ok',
          audio_b64,
          mime_type:   mime,
          duration_ms,
          size_bytes:  size,
        });
      };
      reader.onerror = () => {
        _cleanup();
        resolve({ status: 'error', message: 'FileReader failed to encode audio.' });
      };
      reader.readAsDataURL(blob);
    };

    try {
      _recorder.stop();
    } catch (err) {
      _cleanup();
      resolve({ status: 'error', message: `MediaRecorder.stop() failed: ${err && err.message || String(err)}` });
    }
  });
}

function cancelRecording() {
  if (_recorder && _recorder.state !== 'inactive') {
    try { _recorder.stop(); } catch { /* ignore */ }
  }
  _cleanup();
  return { status: 'ok' };
}

// ---------------------------------------------------------------------------
// Message router
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // Defensive: only handle messages explicitly targeted at the offscreen
  // doc. The service worker uses target:'offscreen' as the discriminator;
  // popup / options page messages will pass through untouched.
  if (!msg || msg.target !== 'offscreen') return false;

  if (msg.action === 'mic-start') {
    startRecording().then(sendResponse).catch((err) =>
      sendResponse({ status: 'error', message: String(err && err.message || err) })
    );
    return true;
  }
  if (msg.action === 'mic-stop') {
    stopRecording().then(sendResponse).catch((err) =>
      sendResponse({ status: 'error', message: String(err && err.message || err) })
    );
    return true;
  }
  if (msg.action === 'mic-cancel') {
    sendResponse(cancelRecording());
    return false;
  }
  if (msg.action === 'ping') {
    // Used by the service worker to verify the offscreen doc is alive
    // without invoking the recorder. Cheap diagnostic.
    sendResponse({
      status:    'ok',
      recording: !!(_recorder && _recorder.state === 'recording'),
      mime_type: _mimeType,
    });
    return false;
  }

  return false;
});

console.log('[Lexora offscreen] mic surface ready');
