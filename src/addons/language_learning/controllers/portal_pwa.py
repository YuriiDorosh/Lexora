"""M36 — Mobile PWA controller.

Two stable PUBLIC routes:

  GET /sw.js               → serves the Service Worker source from
                             language_learning/static/src/js/sw.js with
                             root scope and a no-cache header so update
                             detection works on every page load.

  GET /lexora.webmanifest  → serves the Web App Manifest from
                             language_learning/static/src/manifest.json
                             with the correct application/manifest+json
                             content type.

Both routes are auth='public' (sub-decision 35a + 35g): the SW and the
manifest must be reachable on the very first visit, BEFORE the user
signs in. Authentication-bearing routes (/lexora_api/offline_batch and
/lexora_api/sync_offline) land in S3.

The serving uses odoo.tools.misc.file_open for path-traversal-safe
file access — no string concatenation against user input, no escape
from the addon directory.
"""

import logging
import os

from odoo import http
from odoo.http import request
from odoo.tools import misc as odoo_misc

_logger = logging.getLogger(__name__)

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
