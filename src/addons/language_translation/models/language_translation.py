"""language.translation — async translation job record (SPEC §3.4).

One record per (entry, target_language) pair.  Each record tracks the
full async job lifecycle: pending → processing → completed / failed.

Idempotency: the job_id UUID matches the RabbitMQ message so that
duplicate deliveries are ignored (ADR-018).
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Canonical source of truth — language_words.models.language_lang.LANGUAGE_SELECTION.
# Importing here ensures language.translation.target_language stays in lockstep
# with language.entry.source_language without a duplicated literal.
# (M29 fix: a local copy of this constant was missing 'pl' and caused
# "Wrong value for language.translation.target_language: 'pl'" during backfill.)
from odoo.addons.language_words.models.language_lang import LANGUAGE_SELECTION  # noqa: E402


class LanguageTranslation(models.Model):
    """Translation result for a single learning entry + target language pair."""

    _name = 'language.translation'
    _description = 'Translation'
    _inherit = ['language.job.status.mixin']
    _rec_name = 'target_language'
    _order = 'entry_id, target_language'

    entry_id = fields.Many2one(
        comodel_name='language.entry',
        string='Entry',
        required=True,
        ondelete='cascade',
        index=True,
    )
    target_language = fields.Selection(
        selection=LANGUAGE_SELECTION,
        string='Target Language',
        required=True,
        index=True,
    )
    translated_text = fields.Text(
        string='Translated Text',
        readonly=True,
    )

    _sql_constraints = [
        (
            'unique_entry_target',
            'UNIQUE(entry_id, target_language)',
            'A translation record already exists for this entry and target language.',
        ),
    ]

    # ------------------------------------------------------------------ #
    # Cron: consume result events from RabbitMQ
    # ------------------------------------------------------------------ #

    def action_consume_results(self):
        """Drain translation result queues — called by scheduled cron."""
        from odoo.addons.language_core.models.rabbitmq_consumer import RabbitMQConsumer  # noqa: PLC0415
        consumer = RabbitMQConsumer(self.env)
        consumer.drain('translation.completed', self._handle_completed)
        consumer.drain('translation.failed', self._handle_failed)

    def _handle_completed(self, job_id, payload):
        """Process a translation.completed event."""
        translation = self._find_by_job_id(job_id)
        if not translation:
            _logger.warning('translation.completed: no record for job_id=%s', job_id)
            return
        if translation.status in ('completed', 'failed'):
            _logger.info(
                'translation.completed: duplicate delivery for job_id=%s (status=%s) — skipped',
                job_id, translation.status,
            )
            return
        translation.sudo().write({
            'status': 'completed',
            'translated_text': payload.get('translated_text', ''),
            'error_message': False,
        })
        _logger.info(
            'translation.completed: entry_id=%s lang=%s job_id=%s',
            translation.entry_id.id, translation.target_language, job_id,
        )

    def _handle_failed(self, job_id, payload):
        """Process a translation.failed event."""
        translation = self._find_by_job_id(job_id)
        if not translation:
            _logger.warning('translation.failed: no record for job_id=%s', job_id)
            return
        if translation.status in ('completed', 'failed'):
            _logger.info(
                'translation.failed: duplicate delivery for job_id=%s (status=%s) — skipped',
                job_id, translation.status,
            )
            return
        translation.sudo().write({
            'status': 'failed',
            'error_message': payload.get('error', 'Unknown error'),
        })
        _logger.warning(
            'translation.failed: entry_id=%s lang=%s job_id=%s error=%s',
            translation.entry_id.id, translation.target_language, job_id,
            payload.get('error'),
        )

    def _find_by_job_id(self, job_id):
        """Return the translation record matching job_id, or None."""
        return self.sudo().search([('job_id', '=', job_id)], limit=1) or None

    # ------------------------------------------------------------------ #
    # Portal: retry a failed translation
    # ------------------------------------------------------------------ #

    def action_retry(self):
        """Re-enqueue a failed or stuck translation job."""
        self.ensure_one()
        if self.status not in ('failed', 'pending'):
            raise UserError('Only failed or pending translations can be retried.')
        self._enqueue_single(self.entry_id, self.target_language, translation=self)

    # ------------------------------------------------------------------ #
    # Internal: enqueue helper (also called from language.entry extension)
    # ------------------------------------------------------------------ #

    @api.model
    def _enqueue_single(self, entry, target_language, translation=None):
        """Create (or reset) a translation record and publish the job.

        :param entry:           language.entry record
        :param target_language: str language code
        :param translation:     existing language.translation record (for retry)
        """
        from odoo.addons.language_core.models.rabbitmq_publisher import RabbitMQPublisher  # noqa: PLC0415

        if translation is None:
            # Check whether a record already exists (idempotent create).
            translation = self.sudo().search(
                [('entry_id', '=', entry.id), ('target_language', '=', target_language)],
                limit=1,
            )

        if not translation:
            translation = self.sudo().create({
                'entry_id': entry.id,
                'target_language': target_language,
                'status': 'pending',
            })
        else:
            translation.sudo().write({
                'status': 'pending',
                'error_message': False,
                'translated_text': False,
            })

        job_id = translation._generate_job_id()
        translation.sudo().write({'job_id': job_id, 'status': 'processing'})

        publisher = RabbitMQPublisher(self.env)
        publisher.publish(
            'translation.requested',
            {
                'entry_id': entry.id,
                'source_text': entry.source_text,
                'source_language': entry.source_language,
                'target_language': target_language,
            },
            job_id=job_id,
        )
        return translation
