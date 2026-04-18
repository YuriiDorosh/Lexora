"""Tests for language.anki.job model (M5 foundation).

Covers:
- Model creation and field defaults (job_id auto-set, status=pending)
- _handle_completed populates count fields and details_log
- _handle_completed is idempotent on repeated calls
- _handle_failed sets error_message; idempotent on repeated calls
- Users cannot delete their own job records (perm_unlink=0)
"""

import json

from odoo.tests.common import TransactionCase


class TestLanguageAnkiJob(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'Anki Test User',
            'login': 'anki_test@lexora.test',
            'email': 'anki_test@lexora.test',
            'groups_id': [(6, 0, [cls.env.ref('language_security.group_language_user').id])],
        })
        cls.lang_en = cls.env['language.lang'].search([('code', '=', 'en')], limit=1)
        cls.Job = cls.env['language.anki.job'].sudo()

    def _make_job(self, **kwargs):
        vals = {
            'user_id': self.user.id,
            'filename': 'test_deck.apkg',
            'file_format': 'apkg',
            'source_language_id': self.lang_en.id,
            'entry_type': 'word',
        }
        vals.update(kwargs)
        return self.Job.create(vals)

    def test_job_id_auto_generated(self):
        job = self._make_job()
        self.assertTrue(job.job_id, "job_id should be set automatically on create")
        self.assertEqual(len(job.job_id), 36, "job_id should be a UUID string")

    def test_default_status_pending(self):
        job = self._make_job()
        self.assertEqual(job.status, 'pending')

    def test_handle_completed_updates_counts(self):
        job = self._make_job()
        payload = {
            'entries_created': 12,
            'entries_skipped': 3,
            'entries_failed': 1,
            'skipped_details': json.dumps([{'text': 'duplicate word'}]),
        }
        job._handle_completed(payload)
        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.count_created, 12)
        self.assertEqual(job.count_skipped, 3)
        self.assertEqual(job.count_failed, 1)
        self.assertIn('duplicate word', job.details_log)

    def test_handle_completed_idempotent(self):
        job = self._make_job()
        payload = {'entries_created': 5, 'entries_skipped': 0, 'entries_failed': 0, 'skipped_details': '[]'}
        job._handle_completed(payload)
        # second delivery must be a no-op
        job._handle_completed({'entries_created': 999, 'entries_skipped': 999, 'entries_failed': 999})
        self.assertEqual(job.count_created, 5, "Second delivery must not overwrite completed state")

    def test_handle_failed_sets_error(self):
        job = self._make_job()
        job._handle_failed({'error': 'Unreadable .apkg archive'})
        self.assertEqual(job.status, 'failed')
        self.assertIn('Unreadable', job.error_message)

    def test_handle_failed_idempotent(self):
        job = self._make_job()
        job._handle_failed({'error': 'first error'})
        job._handle_failed({'error': 'second error'})
        self.assertIn('first error', job.error_message, "Second failure must not overwrite terminal state")

    def test_txt_format_accepted(self):
        job = self._make_job(filename='vocab.txt', file_format='txt')
        self.assertEqual(job.file_format, 'txt')

    def test_user_cannot_unlink_own_job(self):
        job = self._make_job()
        with self.assertRaises(Exception):
            job.with_user(self.user).unlink()
