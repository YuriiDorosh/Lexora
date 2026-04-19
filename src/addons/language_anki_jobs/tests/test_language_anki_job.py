"""Tests for language.anki.job model — Phase 1 + Phase 2 (M5).

Phase 1 (M5-01 to M5-04):
- Model creation / field defaults
- _handle_completed / _handle_failed idempotency (consumer signature)

Phase 2 (M5-05 to M5-07):
- action_publish_import: guard (no file_data), status → processing, file_data cleared
- _handle_completed: entry creation, dedup → count_skipped, failed entries, details_log
- _handle_failed: error message written
- Consumer cron wiring (_handle_completed / _handle_failed reachable via job_id lookup)

RabbitMQ is not available in tests; publisher.publish is patched to a no-op.
"""

import base64
import json
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

_PUBLISHER_PATH = (
    'odoo.addons.language_core.models.rabbitmq_publisher.RabbitMQPublisher.publish'
)


def _patch_publish():
    return patch(_PUBLISHER_PATH, return_value='test-job-id')


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
        cls.lang_uk = cls.env['language.lang'].search([('code', '=', 'uk')], limit=1)
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

    def _make_job_with_file(self, **kwargs):
        raw = b'fake-apkg-content'
        b64 = base64.b64encode(raw)
        return self._make_job(file_data=b64, **kwargs)

    # -------------------------------------------------------------------
    # Phase 1 — model basics
    # -------------------------------------------------------------------

    def test_job_id_auto_generated(self):
        job = self._make_job()
        self.assertTrue(job.job_id)
        self.assertEqual(len(job.job_id), 36)

    def test_default_status_pending(self):
        job = self._make_job()
        self.assertEqual(job.status, 'pending')

    def test_txt_format_accepted(self):
        job = self._make_job(filename='vocab.txt', file_format='txt')
        self.assertEqual(job.file_format, 'txt')

    def test_user_cannot_unlink_own_job(self):
        job = self._make_job()
        with self.assertRaises(Exception):
            job.with_user(self.user).unlink()

    def test_file_name_defaults_to_filename(self):
        job = self._make_job()
        self.assertEqual(job.file_name, 'test_deck.apkg')

    # -------------------------------------------------------------------
    # Phase 2 — action_publish_import (M5-05)
    # -------------------------------------------------------------------

    def test_publish_raises_without_file_data(self):
        job = self._make_job()
        with self.assertRaises(UserError):
            job.action_publish_import()

    def test_publish_sets_status_processing(self):
        job = self._make_job_with_file()
        with _patch_publish():
            job.action_publish_import()
        self.assertEqual(job.status, 'processing')

    def test_publish_clears_file_data(self):
        job = self._make_job_with_file()
        with _patch_publish():
            job.action_publish_import()
        self.assertFalse(job.file_data, 'file_data must be cleared after publish')

    def test_publish_calls_rabbitmq(self):
        job = self._make_job_with_file()
        with _patch_publish() as mock_pub:
            job.action_publish_import()
        mock_pub.assert_called_once()
        call_args = mock_pub.call_args
        self.assertEqual(call_args[0][0], 'anki.import.requested')
        payload = call_args[0][1]
        self.assertEqual(payload['job_id'], job.job_id)
        self.assertEqual(payload['source_language'], 'en')
        self.assertEqual(payload['entry_type'], 'word')
        self.assertIn('file_data', payload)

    # -------------------------------------------------------------------
    # Phase 2 — _handle_completed / entry creation (M5-06 / M5-07)
    # -------------------------------------------------------------------

    def test_handle_completed_creates_entries(self):
        job = self._make_job()
        payload = {
            'entries': [
                {'source_text': 'apple'},
                {'source_text': 'banana'},
            ],
            'audio_data': {},
            'parse_errors': [],
        }
        self.Job._handle_completed(job.job_id, payload)
        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.count_created, 2)
        self.assertEqual(job.count_skipped, 0)
        self.assertEqual(job.count_failed, 0)
        # Verify entries actually exist in DB.
        entries = self.env['language.entry'].sudo().search([
            ('owner_id', '=', self.user.id),
            ('source_text', 'in', ['apple', 'banana']),
        ])
        self.assertEqual(len(entries), 2)

    def test_handle_completed_skips_duplicates(self):
        # Pre-create 'apple' so dedup fires on import.
        self.env['language.entry'].sudo().create({
            'source_text': 'apple',
            'source_language': 'en',
            'owner_id': self.user.id,
            'type': 'word',
        })
        job = self._make_job()
        payload = {
            'entries': [
                {'source_text': 'apple'},   # duplicate → skipped
                {'source_text': 'cherry'},  # new → created
            ],
            'audio_data': {},
            'parse_errors': [],
        }
        self.Job._handle_completed(job.job_id, payload)
        self.assertEqual(job.count_created, 1)
        self.assertEqual(job.count_skipped, 1)
        log = json.loads(job.details_log)
        self.assertTrue(any(item.get('reason') == 'duplicate' for item in log))

    def test_handle_completed_counts_parse_errors(self):
        job = self._make_job()
        payload = {
            'entries': [],
            'audio_data': {},
            'parse_errors': [{'reason': 'could not parse card 3'}],
        }
        self.Job._handle_completed(job.job_id, payload)
        self.assertEqual(job.count_failed, 1)
        log = json.loads(job.details_log)
        self.assertIn('could not parse card 3', log[0].get('reason', ''))

    def test_handle_completed_idempotent(self):
        job = self._make_job()
        payload = {
            'entries': [{'source_text': 'mango'}],
            'audio_data': {},
            'parse_errors': [],
        }
        self.Job._handle_completed(job.job_id, payload)
        # Second delivery must be a no-op.
        self.Job._handle_completed(job.job_id, {
            'entries': [{'source_text': 'papaya'}, {'source_text': 'kiwi'}],
            'audio_data': {},
            'parse_errors': [],
        })
        self.assertEqual(job.count_created, 1, 'Second delivery must not overwrite completed state')

    def test_handle_completed_unknown_job_id_is_noop(self):
        # Should log a warning but not raise.
        self.Job._handle_completed('nonexistent-job-id-xxxx', {'entries': []})

    # -------------------------------------------------------------------
    # Phase 2 — _handle_failed (M5-06)
    # -------------------------------------------------------------------

    def test_handle_failed_sets_error(self):
        job = self._make_job()
        self.Job._handle_failed(job.job_id, {'error': 'Unreadable .apkg archive'})
        self.assertEqual(job.status, 'failed')
        self.assertIn('Unreadable', job.error_message)

    def test_handle_failed_idempotent(self):
        job = self._make_job()
        self.Job._handle_failed(job.job_id, {'error': 'first error'})
        self.Job._handle_failed(job.job_id, {'error': 'second error'})
        self.assertIn('first error', job.error_message)
