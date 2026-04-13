import uuid

from odoo import fields, models

JOB_STATUS_SELECTION = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
]


class JobStatusMixin(models.AbstractModel):
    """Abstract mixin for async RabbitMQ job records.

    Every model that tracks an async job (translation, enrichment, audio
    generation, anki import) should inherit this mixin.  It provides:

    - ``job_id``     — UUID used as the idempotency key in every event payload
                       (ADR-018)
    - ``status``     — state machine: pending → processing → completed / failed
    - ``error_message`` — populated on failure for display + retry UI
    """

    _name = 'language.job.status.mixin'
    _description = 'Async Job Status Mixin'

    job_id = fields.Char(
        string='Job ID',
        readonly=True,
        copy=False,
        index=True,
        help='UUID for RabbitMQ event idempotency (ADR-018). Set when the job is enqueued.',
    )
    status = fields.Selection(
        selection=JOB_STATUS_SELECTION,
        string='Status',
        default='pending',
        required=True,
        readonly=True,
        index=True,
    )
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        copy=False,
    )

    def _generate_job_id(self):
        """Return a fresh UUID string suitable for use as a job_id."""
        return str(uuid.uuid4())

    def action_mark_processing(self):
        self.ensure_one()
        self.write({'status': 'processing'})

    def action_mark_completed(self):
        self.ensure_one()
        self.write({'status': 'completed', 'error_message': False})

    def action_mark_failed(self, error_message=''):
        self.ensure_one()
        self.write({'status': 'failed', 'error_message': error_message})
