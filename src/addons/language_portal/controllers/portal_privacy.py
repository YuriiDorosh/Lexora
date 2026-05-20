"""
Lexora — Privacy policy page.

A single public route, /privacy, that serves the canonical privacy
policy.  Chrome Web Store submission requires the privacy policy URL
to be publicly accessible (no login).

The canonical source of truth for the policy text is
`docs/PRIVACY_POLICY.md`.  The QWeb template `portal_privacy_page`
mirrors that content for in-browser display.  When you update the
markdown, also update the template (or vice-versa) — they are
duplicated deliberately so GitHub viewers and Chrome Web Store
reviewers both have direct access.
"""

from odoo import http
from odoo.http import request


class PrivacyController(http.Controller):

    @http.route("/privacy", type="http", auth="public", website=True, sitemap=True)
    def privacy(self, **_kwargs):
        return request.render("language_portal.portal_privacy_page")
