"""language.enrichment — LLM enrichment job record (SPEC §3.5).

One record per (entry, language) pair.  Each record tracks the
full async job lifecycle: pending → processing → completed / failed.

Idempotency: the job_id UUID matches the RabbitMQ message so that
duplicate deliveries are ignored (ADR-018).

Fields returned in the completed payload:
    synonyms          — JSON list of synonym strings
    antonyms          — JSON list of antonym strings
    example_sentences — JSON list of 3–7 sentence strings
    explanation       — short plain-text explanation
"""

import json
import logging
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

LANGUAGE_SELECTION = [
    ('en', 'English'),
    ('uk', 'Ukrainian'),
    ('el', 'Greek'),
]


class LanguageEnrichment(models.Model):
    """LLM enrichment result for a single learning entry + language context."""

    _name = 'language.enrichment'
    _description = 'LLM Enrichment'
    _inherit = ['language.job.status.mixin']
    _rec_name = 'language'
    _order = 'entry_id, language'

    entry_id = fields.Many2one(
        comodel_name='language.entry',
        string='Entry',
        required=True,
        ondelete='cascade',
        index=True,
    )
    language = fields.Selection(
        selection=LANGUAGE_SELECTION,
        string='Language Context',
        required=True,
        index=True,
    )

    # Result fields — populated when status = completed
    synonyms = fields.Text(string='Synonyms (JSON)', readonly=True,
                           help='JSON list of synonym strings')
    antonyms = fields.Text(string='Antonyms (JSON)', readonly=True,
                           help='JSON list of antonym strings')
    example_sentences = fields.Text(string='Example Sentences (JSON)', readonly=True,
                                    help='JSON list of 3–7 example sentences')
    explanation = fields.Text(string='Explanation', readonly=True)

    _sql_constraints = [
        (
            'unique_entry_language',
            'UNIQUE(entry_id, language)',
            'An enrichment record already exists for this entry and language.',
        ),
    ]

    # ------------------------------------------------------------------ #
    # Computed helpers for the portal — parse JSON lists for display
    # ------------------------------------------------------------------ #

    def _synonyms_list(self):
        """Return synonyms as a Python list (empty list on failure)."""
        self.ensure_one()
        try:
            return json.loads(self.synonyms) if self.synonyms else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _antonyms_list(self):
        self.ensure_one()
        try:
            return json.loads(self.antonyms) if self.antonyms else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _example_sentences_list(self):
        self.ensure_one()
        try:
            return json.loads(self.example_sentences) if self.example_sentences else []
        except (json.JSONDecodeError, TypeError):
            return []

    # ------------------------------------------------------------------ #
    # Cron: consume result events from RabbitMQ
    # ------------------------------------------------------------------ #

    def action_consume_results(self):
        """Drain enrichment result queues — called by scheduled cron."""
        from odoo.addons.language_core.models.rabbitmq_consumer import RabbitMQConsumer  # noqa: PLC0415
        consumer = RabbitMQConsumer(self.env)
        consumer.drain('enrichment.completed', self._handle_completed)
        consumer.drain('enrichment.failed', self._handle_failed)

    def _handle_completed(self, job_id, payload):
        """Process an enrichment.completed event."""
        enrichment = self._find_by_job_id(job_id)
        if not enrichment:
            _logger.warning('enrichment.completed: no record for job_id=%s', job_id)
            return
        if enrichment.status in ('completed', 'failed'):
            _logger.info(
                'enrichment.completed: duplicate delivery for job_id=%s (status=%s) — skipped',
                job_id, enrichment.status,
            )
            return

        def _safe_json(val):
            if isinstance(val, list):
                return json.dumps(val)
            return json.dumps([]) if not val else val

        enrichment.sudo().write({
            'status': 'completed',
            'synonyms': _safe_json(payload.get('synonyms')),
            'antonyms': _safe_json(payload.get('antonyms')),
            'example_sentences': _safe_json(payload.get('example_sentences')),
            'explanation': payload.get('explanation', ''),
            'error_message': False,
        })
        _logger.info(
            'enrichment.completed: entry_id=%s lang=%s job_id=%s',
            enrichment.entry_id.id, enrichment.language, job_id,
        )

    def _handle_failed(self, job_id, payload):
        """Process an enrichment.failed event."""
        enrichment = self._find_by_job_id(job_id)
        if not enrichment:
            _logger.warning('enrichment.failed: no record for job_id=%s', job_id)
            return
        if enrichment.status in ('completed', 'failed'):
            _logger.info(
                'enrichment.failed: duplicate delivery for job_id=%s (status=%s) — skipped',
                job_id, enrichment.status,
            )
            return
        enrichment.sudo().write({
            'status': 'failed',
            'error_message': payload.get('error', 'Unknown error'),
        })
        _logger.warning(
            'enrichment.failed: entry_id=%s lang=%s job_id=%s error=%s',
            enrichment.entry_id.id, enrichment.language, job_id,
            payload.get('error'),
        )

    def _find_by_job_id(self, job_id):
        """Return the enrichment record matching job_id, or None."""
        return self.sudo().search([('job_id', '=', job_id)], limit=1) or None

    # ------------------------------------------------------------------ #
    # Portal: retry / trigger
    # ------------------------------------------------------------------ #

    def action_retry(self):
        """Re-enqueue a failed or stuck enrichment job."""
        self.ensure_one()
        if self.status not in ('failed', 'pending'):
            raise UserError('Only failed or pending enrichments can be retried.')
        self._enqueue_single(self.entry_id, self.language, enrichment=self)

    # ------------------------------------------------------------------ #
    # Internal: enqueue helper (called from portal controller)
    # ------------------------------------------------------------------ #

    @api.model
    def _enqueue_single(self, entry, language, enrichment=None):
        """Create (or reset) an enrichment record and publish the job.

        :param entry:      language.entry record
        :param language:   str language code for enrichment context
        :param enrichment: existing language.enrichment record (for retry)
        :returns:          language.enrichment record
        """
        from odoo.addons.language_core.models.rabbitmq_publisher import RabbitMQPublisher  # noqa: PLC0415

        if enrichment is None:
            enrichment = self.sudo().search(
                [('entry_id', '=', entry.id), ('language', '=', language)],
                limit=1,
            )

        if not enrichment:
            enrichment = self.sudo().create({
                'entry_id': entry.id,
                'language': language,
                'status': 'pending',
            })
        else:
            enrichment.sudo().write({
                'status': 'pending',
                'error_message': False,
                'synonyms': False,
                'antonyms': False,
                'example_sentences': False,
                'explanation': False,
            })

        job_id = str(uuid.uuid4())
        enrichment.sudo().write({'job_id': job_id, 'status': 'processing'})

        publisher = RabbitMQPublisher(self.env)
        publisher.publish(
            'enrichment.requested',
            {
                'entry_id': entry.id,
                'source_text': entry.source_text,
                'source_language': entry.source_language,
                'language': language,
            },
            job_id=job_id,
        )
        return enrichment
