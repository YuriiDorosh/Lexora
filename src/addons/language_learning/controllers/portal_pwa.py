"""M36 — Mobile PWA controller.

Public routes (S1):

  GET /sw.js               → serves the Service Worker source from
                             language_learning/static/src/js/sw.js with
                             root scope and a no-cache header so update
                             detection works on every page load.

  GET /lexora.webmanifest  → serves the Web App Manifest from
                             language_learning/static/src/manifest.json
                             with the correct application/manifest+json
                             content type.

Authenticated sync API (S3):

  GET /lexora_api/offline_batch   → prefetch the next N days of due cards
                                    for the caller, with all translations
                                    joined in. Capped at 200 cards / 30
                                    days. JSON envelope.

  POST /lexora_api/sync_offline   → accept a batch of reviews from the
                                    client's offline sync_queue. Idempotent
                                    via language.review.offline.log on
                                    (user_id, client_uuid). All-or-nothing
                                    NOT used — processes everything it can
                                    and reports per-row outcomes.

Public routes are auth='public' (sub-decisions 35a + 35g): the SW and
manifest must be reachable on the very first visit, BEFORE the user
signs in. The sync API uses Odoo's stock auth='user' (sub-decision 35g):
the PWA is served on the same origin as Odoo so the session cookie
travels naturally with every fetch — no X-Lexora-Session-Id bridge
needed.

File serving uses odoo.tools.misc.file_open for path-traversal-safe
access — no string concatenation against user input, no escape from
the addon directory.
"""

import json
import logging
import os
import time

from markupsafe import Markup

from odoo import fields as odoo_fields, http
from odoo.http import request
from odoo.tools import misc as odoo_misc

_logger = logging.getLogger(__name__)

# Tunable defaults for /offline_batch — env-overridable so an operator
# can crank them up on a tablet PWA (more cards per prefetch) without a
# code change. Clamped per-request to safe ranges below.
_OFFLINE_BATCH_DEFAULT_DAYS = int(
    os.environ.get('LEXORA_OFFLINE_BATCH_DEFAULT_DAYS', '7')
)
_OFFLINE_BATCH_DEFAULT_LIMIT = int(
    os.environ.get('LEXORA_OFFLINE_BATCH_DEFAULT_LIMIT', '200')
)
_OFFLINE_BATCH_MAX_DAYS = 30
_OFFLINE_BATCH_MAX_LIMIT = 1000


def _json_body(req):
    """Parse the JSON body of an http-type request defensively.

    Returns ({...}, None) on success or ({}, err_message) on failure.
    Mirrors the parse pattern used by language_portal's M22-M35 routes.
    """
    try:
        raw = req.httprequest.get_data(as_text=True) or ''
        if not raw.strip():
            return {}, None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}, 'JSON body must be an object'
        return data, None
    except json.JSONDecodeError as exc:
        return {}, 'Malformed JSON: %s' % exc


def _project_cards_for_user(env, user, days, limit):
    """Shared card-projection used by BOTH the /lexora_api/offline_batch
    route AND the /my/practice/mobile server-side bootstrap.

    Returns a list of plain dicts shaped per ADR-035 § 35c, so the
    Service Worker, the IndexedDB layer, and the page's
    `<script id="lx-initial-cards">` JSON all agree on a single
    payload format.

    Sort order is identical to language.review.get_due_cards (M7-01)
    so the mobile session feels indistinguishable from the desktop one.
    """
    Review = env['language.review']
    today = odoo_fields.Date.context_today(Review)
    cards = Review.search([
        ('user_id', '=', user.id),
        '|',
            ('next_review_date', '=', False),
            ('next_review_date', '<=',
             odoo_fields.Date.to_string(odoo_fields.Date.add(today, days=days))),
    ], limit=limit, order='state desc, next_review_date asc')

    # Bulk-fetch translations for all entry ids in a single sudo query.
    entry_ids = [c.entry_id.id for c in cards if c.entry_id]
    trans_by_entry = {}
    if entry_ids and 'language.translation' in env.registry:
        Trans = env['language.translation'].sudo()
        for t in Trans.search([
            ('entry_id', 'in', entry_ids),
            ('status', '=', 'completed'),
        ], order='id asc'):
            bucket = trans_by_entry.setdefault(t.entry_id.id, {})
            # First-write wins per (entry, lang) — id-asc means the
            # earliest job's translation is canonical.
            if t.target_language and t.translated_text and \
               t.target_language not in bucket:
                bucket[t.target_language] = t.translated_text

    rows = []
    for c in cards:
        entry = c.entry_id
        if not entry:
            continue
        rows.append({
            'id': c.id,
            'entry_id': entry.id,
            'word': entry.source_text or '',
            'lang': entry.source_language or '',
            'normalized': entry.normalized_text or (entry.source_text or '').lower(),
            'translations': trans_by_entry.get(entry.id) or {},
            'srs_state': c.state,
            'ease_factor': float(c.ease_factor or 0.0),
            'interval': int(c.interval or 0),
            'repetitions': int(c.repetitions or 0),
            'next_review_date_iso': (
                odoo_fields.Date.to_string(c.next_review_date)
                if c.next_review_date else None
            ),
        })
    return rows

# Resolve via __file__ so the path is stable across module install
# locations (development tree vs. /mnt/extra-addons in container).
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SW_REL_PATH = 'static/src/js/sw.js'
_MANIFEST_REL_PATH = 'static/src/manifest.json'


def _read_static_asset(relative_path):
    """Read a file from this addon's static tree.

    Uses odoo.tools.misc.file_open which validates the path against
    Odoo's allowed-roots whitelist — no path traversal possible even
    if a future caller passed user input. The 'rb' mode + bytes
    return is the right shape for serving to make_response.
    """
    full_path = os.path.join('language_learning', relative_path)
    with odoo_misc.file_open(full_path, mode='rb') as fh:
        return fh.read()


class LexoraPwaController(http.Controller):

    # ------------------------------------------------------------------
    # GET /sw.js  — Service Worker (root-scope; see sub-decision 35a)
    # ------------------------------------------------------------------
    @http.route('/sw.js', type='http', auth='public', methods=['GET'], csrf=False)
    def service_worker(self, **kw):
        try:
            body = _read_static_asset(_SW_REL_PATH)
        except (FileNotFoundError, ValueError):
            _logger.exception('sw.js source not found at %s', _SW_REL_PATH)
            return request.make_response('', status=404)

        headers = [
            ('Content-Type', 'application/javascript; charset=utf-8'),
            # Root-scope allowance: lets a SW served from any path under
            # / control requests anywhere under /. Without this header,
            # the SW's scope is implicitly its own path — which here is
            # / anyway, but declaring it explicitly future-proofs the
            # registration if we ever move the controller.
            ('Service-Worker-Allowed', '/'),
            # Critical: browsers consult the SW URL on every page load
            # for update detection. A long cache TTL would break that
            # loop. 'no-cache' = revalidate every time, 'no-store' would
            # be too strict (the browser is allowed to use the cached
            # body as long as it revalidates).
            ('Cache-Control', 'no-cache'),
            # Defensive: explicit length so HEAD requests work cleanly.
            ('Content-Length', str(len(body))),
        ]
        return request.make_response(body, headers=headers)

    # ------------------------------------------------------------------
    # GET /lexora.webmanifest  — Web App Manifest
    # ------------------------------------------------------------------
    @http.route('/lexora.webmanifest', type='http', auth='public',
                methods=['GET'], csrf=False)
    def webmanifest(self, **kw):
        try:
            body = _read_static_asset(_MANIFEST_REL_PATH)
        except (FileNotFoundError, ValueError):
            _logger.exception('manifest.json not found at %s', _MANIFEST_REL_PATH)
            return request.make_response('', status=404)

        headers = [
            # Per the W3C Web App Manifest spec — application/manifest+json
            # is the correct media type. Older browsers also accept
            # application/json but the spec-correct type silences the
            # Chrome DevTools "Manifest: incorrect content type" warning.
            ('Content-Type', 'application/manifest+json; charset=utf-8'),
            # The manifest changes only when we ship a new version; a
            # 1-hour cache is a reasonable balance between snappy first
            # load and the user picking up icon/name changes promptly.
            ('Cache-Control', 'public, max-age=3600'),
            ('Content-Length', str(len(body))),
        ]
        return request.make_response(body, headers=headers)

    # ------------------------------------------------------------------
    # GET /lexora_api/offline_batch  — prefetch the next N days of cards
    # ------------------------------------------------------------------
    @http.route('/lexora_api/offline_batch', type='http', auth='user',
                methods=['GET'], csrf=False)
    def offline_batch(self, days=None, limit=None, **kw):
        """Return due cards + translations for offline review.

        Query params:
            days   — look-ahead window in days. Default
                     LEXORA_OFFLINE_BATCH_DEFAULT_DAYS (7).
                     Clamped to 1..30.
            limit  — max rows. Default
                     LEXORA_OFFLINE_BATCH_DEFAULT_LIMIT (200).
                     Clamped to 1..1000.

        Response shape (see ADR-035 § sub-decision 35c):
            {
              "status": "ok",
              "cards": [
                {
                  "id": <int>,                   # language.review.id
                  "entry_id": <int>,
                  "word": <str>,
                  "lang": <2-letter code>,
                  "normalized": <str>,
                  "translations": {              # lang_code -> str
                    "en": "...", "uk": "...", "el": "...", "pl": "..."
                  },
                  "srs_state": "new" | "learning" | "review",
                  "ease_factor": <float>,
                  "interval": <int>,
                  "repetitions": <int>,
                  "next_review_date_iso": "YYYY-MM-DD" | null
                }
              ],
              "generated_at": <unix int>
            }
        """
        # ── Clamp query params ───────────────────────────────────────
        try:
            d = int(days) if days is not None else _OFFLINE_BATCH_DEFAULT_DAYS
        except (TypeError, ValueError):
            d = _OFFLINE_BATCH_DEFAULT_DAYS
        d = max(1, min(_OFFLINE_BATCH_MAX_DAYS, d))

        try:
            n = int(limit) if limit is not None else _OFFLINE_BATCH_DEFAULT_LIMIT
        except (TypeError, ValueError):
            n = _OFFLINE_BATCH_DEFAULT_LIMIT
        n = max(1, min(_OFFLINE_BATCH_MAX_LIMIT, n))

        rows = _project_cards_for_user(request.env, request.env.user, d, n)
        body = json.dumps({
            'status': 'ok',
            'cards': rows,
            'generated_at': int(time.time()),
        })
        return request.make_response(body, headers=[
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Cache-Control', 'no-store'),     # NEVER cache user data
            ('Content-Length', str(len(body.encode('utf-8')))),
        ])

    # ------------------------------------------------------------------
    # POST /lexora_api/sync_offline  — push queued reviews
    # ------------------------------------------------------------------
    @http.route('/lexora_api/sync_offline', type='http', auth='user',
                methods=['POST'], csrf=False)
    def sync_offline(self, **kw):
        """Process a batch of offline reviews from the client's
        IndexedDB sync_queue.

        Body shape:
            {"reviews": [
                {"client_uuid": "...", "card_id": N,
                 "grade": 0..3, "reviewed_at_iso": "..."}, ...
            ]}

        Response shape:
            {
              "status": "ok",
              "processed":         <int>,
              "skipped_duplicate": <int>,
              "not_found":         <int>,
              "errors":            [{"client_uuid": "...",
                                     "message": "..."}, ...]
            }

        Idempotency: per-row dedup against language.review.offline.log
        on (user_id, client_uuid). The client safely re-uploads the
        same batch after a mid-flight network drop; every UUID already
        in the log is silently counted in skipped_duplicate. The
        delegated apply_offline_batch() method does the heavy lifting
        — the controller is just an HTTP envelope.
        """
        data, err = _json_body(request)
        if err:
            payload = {'status': 'error', 'message': err,
                       'processed': 0, 'skipped_duplicate': 0,
                       'not_found': 0, 'errors': []}
            return _json_http_response(payload, status=400)

        reviews = data.get('reviews')
        if not isinstance(reviews, list):
            payload = {'status': 'error',
                       'message': 'reviews must be a list',
                       'processed': 0, 'skipped_duplicate': 0,
                       'not_found': 0, 'errors': []}
            return _json_http_response(payload, status=400)

        Log = request.env['language.review.offline.log'].sudo()
        result = Log.apply_offline_batch(request.env.user, reviews)
        result['status'] = 'ok'
        return _json_http_response(result)

    # ------------------------------------------------------------------
    # GET /my/practice/mobile  — touch-first SRS review page (PWA shell)
    # ------------------------------------------------------------------
    @http.route('/my/practice/mobile', type='http', auth='user',
                website=True, methods=['GET'])
    def mobile_practice(self, **kw):
        """Render the mobile-practice PWA shell.

        Server-side pre-fetches the first 20 due cards and injects them
        as JSON into the page so the user sees a functional review
        session the instant the HTML lands — before Service Worker
        registration, before IndexedDB opens, before any /offline_batch
        round-trip. On boot, mobile_practice.js reads this initial set
        into IDB on first run; subsequent navigations get the larger
        cache from the previous `/offline_batch` fetch.

        Out of the M36-S1 head-tag injection: this page inherits the
        manifest link, theme-color, and apple-touch-icon via the
        pwa_head_tags.xml inheritance — no duplication.

        The template is a standalone full-viewport layout (NOT
        portal.portal_layout) — no breadcrumbs, no portal navbar, no
        footer credit. It looks like a native app once the user adds it
        to their home screen (sub-decision 35d UX rule).
        """
        # 20 cards is enough to fill ~10 minutes of review at typical
        # pace; the rest of the deck is fetched in the background after
        # SW registration via /offline_batch.
        initial_cards = _project_cards_for_user(
            request.env, request.env.user,
            days=_OFFLINE_BATCH_DEFAULT_DAYS,
            limit=20,
        )
        # JSON embedded inside a <script type="application/json"> tag
        # must NOT be HTML-escaped — the browser doesn't decode HTML
        # entities inside script content, so &#34; would survive into
        # JSON.parse and crash with "Expecting property name enclosed
        # in double quotes". Wrap with markupsafe.Markup to tell QWeb
        # "trust me, this is already safe". The </ → <\/ replacement
        # is the standard XSS shield: a literal </script> inside our
        # payload would otherwise close the script tag prematurely.
        safe_json = json.dumps(initial_cards).replace('</', '<\\/')
        return request.render('language_learning.portal_practice_mobile', {
            'initial_cards': initial_cards,
            'initial_cards_json': Markup(safe_json),
            'user_display_name': request.env.user.name or '',
        })


# Helper kept module-level so both routes (and any future ones)
# share the same response shape.
def _json_http_response(payload, status=200):
    body = json.dumps(payload)
    return request.make_response(body, headers=[
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Cache-Control', 'no-store'),
        ('Content-Length', str(len(body.encode('utf-8')))),
    ], status=status)
