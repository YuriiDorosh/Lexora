from odoo.tests.common import TransactionCase


class TestJobStatusMixin(TransactionCase):
    """Verify the JobStatusMixin abstract model fields and helpers."""

    def test_mixin_is_abstract(self):
        """language.job.status.mixin must be registered as an abstract model."""
        model = self.env['language.job.status.mixin']
        self.assertTrue(model._abstract)

    def test_generate_job_id_is_uuid(self):
        """_generate_job_id() must return a 36-character UUID string."""
        import uuid
        mixin = self.env['language.job.status.mixin']
        job_id = mixin._generate_job_id()
        # Validate it parses as a UUID without raising
        parsed = uuid.UUID(job_id)
        self.assertEqual(str(parsed), job_id)
