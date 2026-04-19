import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

FILE_FORMAT_SELECTION = [
    ('apkg', '.apkg (Anki package)'),
    ('txt', '.txt (tab-separated)'),
]

ENTRY_TYPE_SELECTION = [
    ('word', 'Word'),
    ('phrase', 'Phrase'),
    ('sentence', 'Sentence'),
]


class LanguageAnkiJob(models.Model):
    """Persistent import job record for Anki deck uploads.

    One record per import attempt.  The job_id (from the mixin) is the
    idempotency key carried in every RabbitMQ event (ADR-018).

    Lifecycle:
      pending  →  processing (after action_publish_import)
               →  completed  (after _handle_completed processes the service result)
               →  failed     (after _handle_failed)

    File storage: file_data is cleared after publishing to RabbitMQ so the
    binary content does not persist in the DB after the job is dispatched.
    SPEC §7: ".apkg files — Temp during job processing, not stored after import."
    """

    _name = 'language.anki.job'
    _description = 'Anki Import Job'
    _inherit = 'language.job.status.mixin'
    _order = 'create_date desc'
    _rec_name = 'filename'

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Owner',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.user,
        index=True,
    )
    filename = fields.Char(string='Filename', required=True)
    file_format = fields.Selection(
        selection=FILE_FORMAT_SELECTION,
        string='File Format',
        required=True,
    )
    # Temporary binary storage — cleared after RabbitMQ publish (SPEC §7).
    # attachment=False: stored inline in the DB column, not in the filestore,
    # because this data is intentionally short-lived.
    file_data = fields.Binary(
        string='File Data',
        attachment=False,
        help='Raw upload content.  Cleared after publishing to RabbitMQ.',
    )
    file_name = fields.Char(
        string='File Name',
        help='Odoo binary widget companion — mirrors filename for download label.',
    )
    source_language_id = fields.Many2one(
        comodel_name='language.lang',
        string='Source Language',
        required=True,
        ondelete='restrict',
        help='Language of the source text in the imported deck (confirmed by user at import time).',
    )
    target_language_id = fields.Many2one(
        comodel_name='language.lang',
        string='Destination Language',
        ondelete='restrict',
        help='Language of the translation / back-side text in the deck. '
             'When set, translation records are created immediately from the Anki '
             'data instead of being queued to the translation service.',
    )
    is_pvp_eligible = fields.Boolean(
        string='Mark as PvP Eligible',
        default=False,
        help='Record the user intent that imported entries should be PvP-eligible. '
             'Entries become eligible automatically when Destination Language is set '
             'and completed translation records are created from the Anki data.',
    )
    entry_type = fields.Selection(
        selection=ENTRY_TYPE_SELECTION,
        string='Default Entry Type',
        default='word',
        required=True,
        help='Type assigned to all entries created from this import.',
    )
    field_mapping = fields.Text(
        string='Field Mapping (JSON)',
        help='JSON object mapping deck field names to: source_text, translation. '
             'Auto-detected for .apkg Front/Back convention; user-confirmed before submit.',
    )
    count_created = fields.Integer(string='Entries Created', default=0, readonly=True)
    count_skipped = fields.Integer(string='Entries Skipped', default=0, readonly=True)
    count_failed = fields.Integer(string='Entries Failed', default=0, readonly=True)
    details_log = fields.Text(
        string='Details Log (JSON)',
        readonly=True,
        help='JSON list of skipped / failed items for portal review (SPEC §3.8).',
    )

    # -----------------------------------------------------------------------
    # Create / lifecycle
    # -----------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('job_id'):
                vals['job_id'] = self._generate_job_id()
            if not vals.get('file_name') and vals.get('filename'):
                vals['file_name'] = vals['filename']
        return super().create(vals_list)

    # -----------------------------------------------------------------------
    # M5-05: Publisher
    # -----------------------------------------------------------------------

    def action_publish_import(self):
        """Publish anki.import.requested to RabbitMQ.

        Validates that file_data is present, encodes the payload, marks the
        job as processing, and clears file_data from the DB after dispatch.

        Raises UserError if file_data is missing (guard for portal misuse).
        """
        self.ensure_one()
        if not self.file_data:
            raise UserError(
                'No file data found on this import job.  '
                'Please upload the file before submitting.'
            )

        # file_data is already base64-encoded bytes in the Odoo ORM.
        file_b64 = self.file_data.decode('utf-8') if isinstance(self.file_data, bytes) else self.file_data

        payload = {
            'job_id': self.job_id,
            'user_id': self.user_id.id,
            'source_language': self.source_language_id.code,
            'entry_type': self.entry_type,
            'file_format': self.file_format,
            'field_mapping': self.field_mapping or '{}',
            'file_data': file_b64,
        }

        from odoo.addons.language_core.models.rabbitmq_publisher import RabbitMQPublisher  # noqa: PLC0415
        publisher = RabbitMQPublisher(self.env)
        publisher.publish('anki.import.requested', payload, self.job_id)

        # Mark processing and clear stored binary (SPEC §7: not stored after dispatch).
        self.sudo().write({
            'status': 'processing',
            'file_data': False,
        })
        _logger.info('anki.import.requested published: job_id=%s filename=%s', self.job_id, self.filename)

    # -----------------------------------------------------------------------
    # M5-06: Consumer cron entry-point
    # -----------------------------------------------------------------------

    def action_consume_results(self):
        """Drain anki result queues — called by scheduled cron."""
        from odoo.addons.language_core.models.rabbitmq_consumer import RabbitMQConsumer  # noqa: PLC0415
        consumer = RabbitMQConsumer(self.env)
        consumer.drain('anki.import.completed', self._handle_completed)
        consumer.drain('anki.import.failed', self._handle_failed)

    # -----------------------------------------------------------------------
    # M5-06/07: Result handlers
    # -----------------------------------------------------------------------

    def _find_by_job_id(self, job_id):
        return self.sudo().search([('job_id', '=', job_id)], limit=1)

    def _handle_completed(self, job_id, payload):
        """Process an anki.import.completed event.

        Creates language.entry records for each parsed entry in the payload,
        using savepoints so that dedup ValidationErrors on individual entries
        only skip that entry rather than rolling back the entire batch.
        Audio data in the payload is forwarded to _create_audio_records if
        language.audio is available (M6+).
        """
        job = self._find_by_job_id(job_id)
        if not job:
            _logger.warning('anki.import.completed: no job record for job_id=%s', job_id)
            return
        if job.status in ('completed', 'failed'):
            _logger.info(
                'anki.import.completed: duplicate delivery job_id=%s (status=%s) — skipped',
                job_id, job.status,
            )
            return

        entries = payload.get('entries', [])
        audio_data = payload.get('audio_data', {})
        parse_errors = payload.get('parse_errors', [])

        count_created = 0
        count_skipped = 0
        count_failed = len(parse_errors)
        skipped_details = list(parse_errors)

        source_lang_code = job.source_language_id.code
        target_lang_code = job.target_language_id.code if job.target_language_id else None
        created_entry_map = {}  # audio_filename → entry_id for audio linking

        # Lazy: language.translation may not be loaded in tests that only install
        # language_anki_jobs.  Only resolve when target_language_id is actually set.
        TransModel = None
        if target_lang_code:
            try:
                TransModel = self.env['language.translation'].sudo()
            except KeyError:
                _logger.warning(
                    'language.translation not available — skipping direct translation creation'
                )
                target_lang_code = None

        for entry_vals_raw in entries:
            source_text = entry_vals_raw.get('source_text', '').strip()
            if not source_text:
                count_failed += 1
                continue

            create_vals = {
                'source_text': source_text,
                'source_language': source_lang_code,
                'owner_id': job.user_id.id,
                'type': job.entry_type,
                'created_from': 'anki_import',
            }
            audio_filename = entry_vals_raw.get('audio_filename')
            translation_text = entry_vals_raw.get('translation', '').strip()

            try:
                with self.env.cr.savepoint():
                    entry = self.env['language.entry'].sudo().create(create_vals)
                    count_created += 1
                    if audio_filename:
                        created_entry_map[audio_filename] = entry.id

                    # Create a completed translation record immediately from the
                    # Anki back-side text, bypassing the translation service.
                    if target_lang_code and translation_text and target_lang_code != source_lang_code:
                        existing_trans = TransModel.search([
                            ('entry_id', '=', entry.id),
                            ('target_language', '=', target_lang_code),
                        ], limit=1)
                        if not existing_trans:
                            TransModel.create({
                                'entry_id': entry.id,
                                'target_language': target_lang_code,
                                'translated_text': translation_text,
                                'status': 'completed',
                            })
                            _logger.debug(
                                'anki.import: created direct translation for entry %d → %s',
                                entry.id, target_lang_code,
                            )

            except ValidationError:
                count_skipped += 1
                skipped_details.append({
                    'source_text': source_text,
                    'reason': 'duplicate',
                })
            except Exception as exc:
                count_failed += 1
                skipped_details.append({
                    'source_text': source_text,
                    'reason': str(exc),
                })
                _logger.warning(
                    'anki.import: failed to create entry %r for job_id=%s: %s',
                    source_text, job_id, exc,
                )

        # Audio attachment — deferred gracefully when language.audio isn't installed yet.
        if audio_data and created_entry_map:
            self._create_audio_records(created_entry_map, audio_data)

        job.sudo().write({
            'status': 'completed',
            'count_created': count_created,
            'count_skipped': count_skipped,
            'count_failed': count_failed,
            'details_log': json.dumps(skipped_details, ensure_ascii=False),
            'error_message': False,
        })
        _logger.info(
            'anki.import.completed: job_id=%s created=%d skipped=%d failed=%d',
            job_id, count_created, count_skipped, count_failed,
        )

    def _handle_failed(self, job_id, payload):
        """Process an anki.import.failed event."""
        job = self._find_by_job_id(job_id)
        if not job:
            _logger.warning('anki.import.failed: no job record for job_id=%s', job_id)
            return
        if job.status in ('completed', 'failed'):
            _logger.info(
                'anki.import.failed: duplicate delivery job_id=%s (status=%s) — skipped',
                job_id, job.status,
            )
            return
        job.sudo().write({
            'status': 'failed',
            'error_message': payload.get('error', 'Unknown error from Anki service'),
        })
        _logger.warning('anki.import.failed: job_id=%s error=%s', job_id, payload.get('error'))

    def _create_audio_records(self, entry_audio_map, audio_data):
        """Create language.audio records for extracted .apkg audio (M6+).

        entry_audio_map: {audio_filename: entry_id}
        audio_data:      {audio_filename: base64_mp3_string}

        Silently skips if language.audio model is not installed yet — it
        becomes active automatically once M6 lands.
        """
        try:
            AudioModel = self.env['language.audio']
        except KeyError:
            _logger.debug('language.audio not available (pre-M6); audio attachment skipped')
            return

        for audio_filename, entry_id in entry_audio_map.items():
            b64_data = audio_data.get(audio_filename)
            if not b64_data:
                continue
            try:
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': audio_filename,
                    'datas': b64_data,
                    'res_model': 'language.entry',
                    'res_id': entry_id,
                    'mimetype': 'audio/mpeg',
                })
                AudioModel.sudo().create({
                    'entry_id': entry_id,
                    'audio_type': 'imported',
                    'attachment_id': attachment.id,
                })
            except Exception as exc:
                _logger.warning(
                    'anki.import: failed to attach audio %r to entry %d: %s',
                    audio_filename, entry_id, exc,
                )
