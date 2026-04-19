"""Translation portal controller — retry, manual trigger, inline edit."""

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

SUPPORTED_LANG_CODES = {'en', 'uk', 'el'}


class TranslationPortal(http.Controller):

    # ------------------------------------------------------------------
    # Retry a failed translation
    # POST /my/vocabulary/<entry_id>/retry_translation/<translation_id>
    # ------------------------------------------------------------------

    @http.route(
        '/my/vocabulary/<int:entry_id>/retry_translation/<int:translation_id>',
        type='http', auth='user', website=True, methods=['POST'],
    )
    def retry_translation(self, entry_id, translation_id, **post):
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

    # ------------------------------------------------------------------
    # Manually trigger translation for a specific language
    # POST /my/vocabulary/<entry_id>/translate/<lang_code>
    # ------------------------------------------------------------------

    @http.route(
        '/my/vocabulary/<int:entry_id>/translate/<string:lang_code>',
        type='http', auth='user', website=True, methods=['POST'],
    )
    def trigger_translation(self, entry_id, lang_code, **post):
        if lang_code not in SUPPORTED_LANG_CODES:
            return request.not_found()

        entry = request.env['language.entry'].browse(entry_id)
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()

        if lang_code == entry.source_language:
            return request.redirect('/my/vocabulary/%d' % entry_id)

        try:
            request.env['language.translation']._enqueue_single(entry, lang_code)
        except Exception as exc:
            _logger.warning('Manual translation trigger failed: %s', exc)

        return request.redirect('/my/vocabulary/%d' % entry_id)

    # ------------------------------------------------------------------
    # Inline edit — update translated_text manually
    # POST /my/translation/update/<trans_id>
    # ------------------------------------------------------------------

    @http.route(
        '/my/translation/update/<int:trans_id>',
        type='http', auth='user', website=True, methods=['POST'],
    )
    def update_translation(self, trans_id, **post):
        translation = request.env['language.translation'].sudo().browse(trans_id)
        if not translation.exists():
            return request.not_found()

        # Ownership check via the parent entry.
        entry = translation.entry_id
        if not entry.exists() or entry.owner_id.id != request.env.user.id:
            return request.not_found()

        new_text = (post.get('translated_text') or '').strip()
        if new_text:
            translation.sudo().write({
                'translated_text': new_text,
                'status': 'completed',
                'error_message': False,
            })
            _logger.info(
                'Portal: user %s manually updated translation %d → %r',
                request.env.user.login, trans_id, new_text[:60],
            )

        return request.redirect('/my/vocabulary/%d' % entry.id)
