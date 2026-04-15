"""Portal routes for LLM enrichment — trigger and retry."""

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EnrichmentPortalController(http.Controller):

    @http.route(
        '/my/vocabulary/<int:entry_id>/enrich',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=True,
    )
    def trigger_enrichment(self, entry_id, **kwargs):
        """Trigger LLM enrichment for an entry (user-initiated)."""
        entry = request.env['language.entry'].sudo().search(
            [('id', '=', entry_id), ('owner_id', '=', request.env.uid)],
            limit=1,
        )
        if not entry:
            return request.not_found()

        # Enrich in the entry's source language context
        request.env['language.enrichment'].sudo()._enqueue_single(
            entry, entry.source_language
        )
        return request.redirect('/my/vocabulary/%d' % entry_id)

    @http.route(
        '/my/vocabulary/<int:entry_id>/retry_enrichment/<int:enrichment_id>',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=True,
    )
    def retry_enrichment(self, entry_id, enrichment_id, **kwargs):
        """Retry a failed enrichment job."""
        entry = request.env['language.entry'].sudo().search(
            [('id', '=', entry_id), ('owner_id', '=', request.env.uid)],
            limit=1,
        )
        if not entry:
            return request.not_found()

        enrichment = request.env['language.enrichment'].sudo().search(
            [('id', '=', enrichment_id), ('entry_id', '=', entry_id)],
            limit=1,
        )
        if not enrichment:
            return request.not_found()

        try:
            enrichment.action_retry()
        except Exception as exc:  # noqa: BLE001
            _logger.warning('Enrichment retry failed: %s', exc)

        return request.redirect('/my/vocabulary/%d' % entry_id)
