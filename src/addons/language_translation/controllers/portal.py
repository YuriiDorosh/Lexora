"""Translation portal controller — extends vocabulary portal with retry action."""

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TranslationPortal(http.Controller):
    """Adds the retry route for failed translations.

    Route:  POST /my/vocabulary/<entry_id>/retry_translation/<translation_id>
    """

    @http.route(
        '/my/vocabulary/<int:entry_id>/retry_translation/<int:translation_id>',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
    )
    def retry_translation(self, entry_id, translation_id, **post):
        # Verify the entry belongs to the current user.
        entry = request.env['language.entry'].browse(entry_id)
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()

        translation = request.env['language.translation'].browse(translation_id)
        if not translation.exists() or translation.entry_id.id != entry_id:
            return request.not_found()

        try:
            translation.action_retry()
        except Exception as exc:
            _logger.warning('Translation retry failed: %s', exc)

        return request.redirect('/my/vocabulary/%d' % entry_id)
