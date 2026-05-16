/**
 * extension/youtube_radar_inject.js — runs in the page's MAIN WORLD.
 *
 * Loaded by extension/youtube_radar.js via a <script src=getURL(...)> tag
 * appended to document.documentElement (see ADR-033 sub-decision 34b).
 *
 * Why main-world: MV3 content scripts run in an isolated world and can't
 * read response bodies from page-issued XHR / fetch. To get look-ahead
 * into YouTube's caption track (the M34 radar needs to pause BEFORE a
 * word is spoken — DOM observation only sees the cue AT the word, too
 * late), we patch XMLHttpRequest.prototype + window.fetch here, sniff
 * for /api/timedtext, parse the JSON3 (modern) or SRV3/XML (fallback)
 * payload, and post the normalised cue array back to the content script
 * via window.postMessage.
 *
 * Safety contract: every patch is wrapped so that an exception inside
 * our hook NEVER breaks the page's own request flow. response.clone()
 * is used for fetch so we don't consume the body the page itself will
 * read. The idempotent guard at the top of the IIFE survives double
 * injection on SPA navigation (yt-navigate-finish fires once per
 * route change).
 *
 * Message format:
 *   {source: 'lx-radar', type: 'cues', cues: [{startMs, endMs, text}, ...]}
 *   {source: 'lx-radar', type: 'ready'}   — fired once after patches land
 *
 * The content script filters every message by source === 'lx-radar' so
 * a stray postMessage from another extension can't poison the timeline.
 */

(function () {
  'use strict';

  // ── Idempotent guard ──────────────────────────────────────────────────
  // SPA navigation on youtube.com fires yt-navigate-finish events that may
  // trigger our content script to re-inject this file. A second IIFE
  // execution would double-patch fetch / XHR, double-emit cues, and
  // double-warn on every event. The guard short-circuits the re-entry.
  if (window.__lxRadarInjected) {
    return;
  }
  window.__lxRadarInjected = true;

  var TIMEDTEXT_RE = /^https?:\/\/[^/]*\.youtube\.com\/api\/timedtext\b/i;
  var MSG_SOURCE = 'lx-radar';

  function _post(envelope) {
    try {
      window.postMessage(envelope, '*');
    } catch (e) {
      // Should never happen for plain JSON-serialisable payloads, but
      // log so the content script's silence has a paper trail in the
      // page's own console.
      console.warn('[lx-radar inject] postMessage failed:', e);
    }
  }

  function _emitCues(cues) {
    if (!cues || !cues.length) return;
    _post({source: MSG_SOURCE, type: 'cues', cues: cues});
  }

  // ── Body parser: JSON3 primary, SRV1/SRV3 XML fallback ────────────────

  function _parseBody(text) {
    if (!text || typeof text !== 'string') return [];
    // Strip any leading BOM / whitespace before sniffing the first byte.
    var t = text.replace(/^[﻿\s]+/, '');
    if (!t) return [];

    if (t.charAt(0) === '{') {
      try {
        var obj = JSON.parse(t);
        if (obj && Array.isArray(obj.events)) return _parseJson3(obj.events);
      } catch (e) {
        // fall through to XML attempt
      }
    }

    if (t.charAt(0) === '<') {
      return _parseXml(t);
    }

    // One-time warning per page load to flag a new format.
    if (!window.__lxRadarUnknownFormatLogged) {
      window.__lxRadarUnknownFormatLogged = true;
      console.warn('[lx-radar inject] unknown timedtext format; first 60 chars:', t.slice(0, 60));
    }
    return [];
  }

  function _parseJson3(events) {
    var cues = [];
    for (var i = 0; i < events.length; i++) {
      var ev = events[i];
      if (!ev || !Array.isArray(ev.segs)) continue; // silence / window markers
      var parts = [];
      for (var j = 0; j < ev.segs.length; j++) {
        var seg = ev.segs[j];
        if (seg && typeof seg.utf8 === 'string') parts.push(seg.utf8);
      }
      var cueText = parts.join('').replace(/\s+/g, ' ').trim();
      if (!cueText) continue;
      var startMs = Number(ev.tStartMs);
      if (!isFinite(startMs)) startMs = 0;
      var durMs = Number(ev.dDurationMs);
      if (!isFinite(durMs) || durMs < 0) durMs = 0;
      cues.push({startMs: startMs, endMs: startMs + durMs, text: cueText});
    }
    return cues;
  }

  function _parseXml(xmlText) {
    try {
      var doc = new DOMParser().parseFromString(xmlText, 'text/xml');
      if (doc.getElementsByTagName('parsererror').length) return [];

      var cues = [];

      // SRV3 modern: <p t="ms" d="ms">text</p>
      var pNodes = doc.getElementsByTagName('p');
      if (pNodes && pNodes.length) {
        for (var i = 0; i < pNodes.length; i++) {
          var p = pNodes[i];
          var pStart = Number(p.getAttribute('t')) || 0;
          var pDur = Number(p.getAttribute('d')) || 0;
          var pText = (p.textContent || '').replace(/\s+/g, ' ').trim();
          if (pText) {
            cues.push({startMs: pStart, endMs: pStart + pDur, text: pText});
          }
        }
        if (cues.length) return cues;
      }

      // SRV1 legacy: <text start="seconds" dur="seconds">text</text>
      var textNodes = doc.getElementsByTagName('text');
      if (textNodes && textNodes.length) {
        for (var k = 0; k < textNodes.length; k++) {
          var t = textNodes[k];
          var tStartS = Number(t.getAttribute('start')) || 0;
          var tDurS = Number(t.getAttribute('dur')) || 0;
          var tText = (t.textContent || '').replace(/\s+/g, ' ').trim();
          if (tText) {
            cues.push({
              startMs: Math.round(tStartS * 1000),
              endMs:   Math.round((tStartS + tDurS) * 1000),
              text:    tText,
            });
          }
        }
        return cues;
      }

      return [];
    } catch (e) {
      console.warn('[lx-radar inject] XML parse failed:', e);
      return [];
    }
  }

  function _ingest(text) {
    var cues = _parseBody(text);
    if (cues.length) _emitCues(cues);
  }

  // ── XMLHttpRequest patch ──────────────────────────────────────────────
  try {
    var XhrProto = window.XMLHttpRequest && window.XMLHttpRequest.prototype;
    if (XhrProto && typeof XhrProto.open === 'function' && typeof XhrProto.send === 'function') {
      var origOpen = XhrProto.open;
      var origSend = XhrProto.send;

      XhrProto.open = function (method, url) {
        try {
          // Stash the URL on the instance so send() can decide whether
          // to attach a load listener. Don't fight with non-writable
          // properties — fall back silently if the page froze the
          // prototype contract.
          this.__lxUrl = String(url == null ? '' : url);
        } catch (e) {
          // ignore
        }
        return origOpen.apply(this, arguments);
      };

      XhrProto.send = function () {
        var self = this;
        try {
          if (self.__lxUrl && TIMEDTEXT_RE.test(self.__lxUrl)) {
            self.addEventListener('load', function () {
              try {
                if (self.status >= 200 && self.status < 300) {
                  // responseText is the safe accessor for text/* and
                  // application/json with default responseType; for
                  // 'arraybuffer' / 'blob' it throws — caught below.
                  _ingest(self.responseText);
                }
              } catch (loadErr) {
                console.warn('[lx-radar inject] XHR load handler failed:', loadErr);
              }
            });
          }
        } catch (e) {
          // Never let our hook break the page's own request.
        }
        return origSend.apply(this, arguments);
      };
    }
  } catch (e) {
    console.warn('[lx-radar inject] XHR patch failed:', e);
  }

  // ── fetch patch ───────────────────────────────────────────────────────
  try {
    if (typeof window.fetch === 'function') {
      var origFetch = window.fetch.bind(window);

      window.fetch = function (input, init) {
        var url = '';
        try {
          if (typeof input === 'string') {
            url = input;
          } else if (input && typeof input.url === 'string') {
            // Request object
            url = input.url;
          } else if (input && typeof input.href === 'string') {
            // URL object
            url = input.href;
          }
        } catch (e) {
          // ignore — URL inspection should never break the request
        }

        var promise = origFetch(input, init);

        if (url && TIMEDTEXT_RE.test(url)) {
          // Tap into the response without disturbing the page's own
          // consumer. .clone() forks the body so both the page and
          // our handler can read it.
          promise.then(function (resp) {
            if (!resp || !resp.ok) return;
            try {
              resp.clone().text().then(_ingest).catch(function (err) {
                console.warn('[lx-radar inject] fetch body read failed:', err);
              });
            } catch (cloneErr) {
              console.warn('[lx-radar inject] response.clone failed:', cloneErr);
            }
          }).catch(function () {
            // Page-level fetch rejection; nothing for us to do.
          });
        }

        return promise;
      };
    }
  } catch (e) {
    console.warn('[lx-radar inject] fetch patch failed:', e);
  }

  // ── Ready signal ──────────────────────────────────────────────────────
  // Helps the content script confirm the patches landed before it begins
  // listening; also a useful diagnostic in the page's console.
  _post({source: MSG_SOURCE, type: 'ready'});
})();
