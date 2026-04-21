/**
 * Lexora Spotlight Search — Ctrl+K / ⌘K global search overlay.
 *
 * Opens a modal, sends debounced requests to GET /search?q=<query>,
 * renders grouped results (vocabulary, grammar, gold words, posts),
 * and supports keyboard navigation.
 */
(function () {
    'use strict';

    var _debounceTimer = null;
    var _activeIdx = -1;

    function buildModal() {
        var existing = document.getElementById('lexora-spotlight-modal');
        if (existing) return existing;

        var modal = document.createElement('div');
        modal.id = 'lexora-spotlight-modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-label', 'Quick Search');
        modal.innerHTML = [
            '<div id="lexora-spotlight-backdrop"></div>',
            '<div id="lexora-spotlight-box">',
            '  <div id="lexora-spotlight-input-wrap">',
            '    <span id="lexora-spotlight-icon">🔍</span>',
            '    <input id="lexora-spotlight-input" type="text"',
            '           placeholder="Search vocabulary, grammar, words…"',
            '           autocomplete="off" spellcheck="false"/>',
            '    <kbd id="lexora-spotlight-esc">Esc</kbd>',
            '  </div>',
            '  <div id="lexora-spotlight-results"></div>',
            '</div>',
        ].join('');

        var style = document.createElement('style');
        style.textContent = [
            '#lexora-spotlight-modal{position:fixed;inset:0;z-index:9999;display:none}',
            '#lexora-spotlight-modal.open{display:block}',
            '#lexora-spotlight-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.45);cursor:pointer}',
            '#lexora-spotlight-box{position:fixed;top:12vh;left:50%;transform:translateX(-50%);',
            '  width:min(640px,92vw);background:#fff;border-radius:12px;',
            '  box-shadow:0 24px 64px rgba(0,0,0,.25);overflow:hidden;font-size:15px}',
            '#lexora-spotlight-input-wrap{display:flex;align-items:center;gap:8px;padding:14px 16px;',
            '  border-bottom:1px solid #e5e7eb}',
            '#lexora-spotlight-icon{font-size:18px;flex-shrink:0}',
            '#lexora-spotlight-input{flex:1;border:none;outline:none;font-size:16px;background:transparent}',
            '#lexora-spotlight-esc{background:#f3f4f6;border:1px solid #d1d5db;border-radius:4px;',
            '  padding:2px 6px;font-size:11px;color:#6b7280;cursor:pointer;flex-shrink:0}',
            '#lexora-spotlight-results{max-height:60vh;overflow-y:auto;padding:8px 0}',
            '.sl-group{padding:6px 16px 2px;font-size:11px;font-weight:600;',
            '  text-transform:uppercase;letter-spacing:.06em;color:#9ca3af}',
            '.sl-item{display:flex;align-items:center;gap:10px;padding:9px 16px;',
            '  cursor:pointer;transition:background .12s;text-decoration:none;color:inherit}',
            '.sl-item:hover,.sl-item.active{background:#f0f4ff}',
            '.sl-item-icon{font-size:16px;flex-shrink:0;width:22px;text-align:center}',
            '.sl-item-body{flex:1;min-width:0}',
            '.sl-item-title{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
            '.sl-item-sub{font-size:12px;color:#6b7280;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
            '.sl-empty{padding:24px 16px;text-align:center;color:#9ca3af;font-size:14px}',
            '.sl-hint{padding:8px 16px;font-size:12px;color:#9ca3af;border-top:1px solid #f3f4f6;',
            '  display:flex;gap:16px}',
            '.sl-hint kbd{background:#f3f4f6;border:1px solid #d1d5db;border-radius:3px;',
            '  padding:1px 5px;font-size:11px}',
        ].join('');
        document.head.appendChild(style);
        document.body.appendChild(modal);
        return modal;
    }

    function openSpotlight() {
        var modal = buildModal();
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
        var input = document.getElementById('lexora-spotlight-input');
        if (input) {
            input.value = '';
            input.focus();
        }
        renderResults(null);
    }

    function closeSpotlight() {
        var modal = document.getElementById('lexora-spotlight-modal');
        if (modal) modal.classList.remove('open');
        document.body.style.overflow = '';
        _activeIdx = -1;
    }

    function renderResults(data) {
        var box = document.getElementById('lexora-spotlight-results');
        if (!box) return;
        if (!data) {
            box.innerHTML = '<div class="sl-empty">Type to search across your vocabulary, grammar guides and more…</div>';
            return;
        }
        var groups = data.groups || [];
        if (!groups.length) {
            box.innerHTML = '<div class="sl-empty">No results found.</div>';
            return;
        }
        var html = '';
        var icons = {vocabulary: '📝', grammar: '📖', words: '🔤', posts: '📰'};
        groups.forEach(function (g) {
            html += '<div class="sl-group">' + escHtml(g.label) + '</div>';
            g.items.forEach(function (item) {
                html += '<a class="sl-item" href="' + escHtml(item.url) + '">'
                    + '<span class="sl-item-icon">' + (icons[g.type] || '•') + '</span>'
                    + '<span class="sl-item-body">'
                    + '<div class="sl-item-title">' + escHtml(item.title) + '</div>'
                    + (item.sub ? '<div class="sl-item-sub">' + escHtml(item.sub) + '</div>' : '')
                    + '</span></a>';
            });
        });
        html += '<div class="sl-hint">'
            + '<span><kbd>↑↓</kbd> navigate</span>'
            + '<span><kbd>Enter</kbd> open</span>'
            + '<span><kbd>Esc</kbd> close</span>'
            + '</div>';
        box.innerHTML = html;
        _activeIdx = -1;
    }

    function escHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function moveSelection(dir) {
        var items = document.querySelectorAll('#lexora-spotlight-results .sl-item');
        if (!items.length) return;
        items.forEach(function (el) { el.classList.remove('active'); });
        _activeIdx = (_activeIdx + dir + items.length) % items.length;
        items[_activeIdx].classList.add('active');
        items[_activeIdx].scrollIntoView({block: 'nearest'});
    }

    function activateSelected() {
        var item = document.querySelector('#lexora-spotlight-results .sl-item.active');
        if (item) { window.location.href = item.href; }
    }

    function doSearch(q) {
        if (!q) { renderResults(null); return; }
        fetch('/search?q=' + encodeURIComponent(q) + '&format=json', {
            headers: {'X-Requested-With': 'XMLHttpRequest'},
            credentials: 'same-origin',
        })
        .then(function (r) { return r.json(); })
        .then(function (data) { renderResults(data); })
        .catch(function () { renderResults({groups: []}); });
    }

    document.addEventListener('DOMContentLoaded', function () {
        buildModal();

        document.getElementById('lexora-spotlight-backdrop').addEventListener('click', closeSpotlight);
        document.getElementById('lexora-spotlight-esc').addEventListener('click', closeSpotlight);

        var input = document.getElementById('lexora-spotlight-input');
        input.addEventListener('input', function () {
            clearTimeout(_debounceTimer);
            var q = input.value.trim();
            _debounceTimer = setTimeout(function () { doSearch(q); }, 220);
        });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); moveSelection(1); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); moveSelection(-1); }
            else if (e.key === 'Enter') { e.preventDefault(); activateSelected(); }
            else if (e.key === 'Escape') { closeSpotlight(); }
        });

        document.addEventListener('keydown', function (e) {
            var modal = document.getElementById('lexora-spotlight-modal');
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                if (modal && modal.classList.contains('open')) { closeSpotlight(); }
                else { openSpotlight(); }
            }
            if (e.key === 'Escape' && modal && modal.classList.contains('open')) {
                closeSpotlight();
            }
        });
    });
})();
