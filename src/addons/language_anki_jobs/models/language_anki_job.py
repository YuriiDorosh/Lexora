from odoo import api, fields, models

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
    skipped_details / details_log are stored as JSON so the portal can
    render a reviewable list of skipped / failed items (SPEC §3.8).
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
    source_language_id = fields.Many2one(
        comodel_name='language.lang',
        string='Source Language',
        required=True,
        ondelete='restrict',
        help='Language of the source text in the imported deck (confirmed by user at import time).',
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('job_id'):
                vals['job_id'] = self._generate_job_id()
        return super().create(vals_list)

    def _handle_completed(self, payload: dict):
        """Called by the Odoo RabbitMQ consumer on anki.import.completed."""
        self.ensure_one()
        if self.status in ('completed', 'failed'):
            return
        self.write({
            'status': 'completed',
            'count_created': payload.get('entries_created', 0),
            'count_skipped': payload.get('entries_skipped', 0),
            'count_failed': payload.get('entries_failed', 0),
            'details_log': payload.get('skipped_details', '[]'),
            'error_message': False,
        })

    def _handle_failed(self, payload: dict):
        """Called by the Odoo RabbitMQ consumer on anki.import.failed."""
        self.ensure_one()
        if self.status in ('completed', 'failed'):
            return
        self.write({
            'status': 'failed',
            'error_message': payload.get('error', 'Unknown error'),
        })
