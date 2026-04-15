"""Tests for language_enrichment: model, state machine, idempotency, retry, enqueue."""

import json
from contextlib import contextmanager
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestLanguageEnrichment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a test user with the Language User group (matching M3 test pattern)
        cls.user = cls.env['res.users'].create({
            'name': 'Enrichment Test User',
            'login': 'enrichment_test_user@test.com',
            'email': 'enrichment_test_user@test.com',
            'groups_id': [(6, 0, [cls.env.ref('language_security.group_language_user').id])],
        })

        # Give user a language profile with native=en
        profile = cls.env['language.user.profile']._get_or_create_for_user(cls.user)
        profile.sudo().write({'native_language': 'en'})

        cls.Entry = cls.env['language.entry'].sudo()
        cls.Enrichment = cls.env['language.enrichment'].sudo()

    @contextmanager
    def _patch_publish(self):
        """Suppress RabbitMQ publish calls during tests."""
        with patch(
            'odoo.addons.language_core.models.rabbitmq_publisher.RabbitMQPublisher.publish'
        ) as mock_pub:
            yield mock_pub

    def _make_entry(self, source_text='apple', source_language='en'):
        """Create a language.entry owned by test user (auto-enqueues translation, not enrichment)."""
        with self._patch_publish():
            return self.Entry.create({
                'source_text': source_text,
                'source_language': source_language,
                'type': 'word',
                'owner_id': self.user.id,
            })

    def _make_enrichment(self, entry=None, language='en', status='pending'):
        """Create an enrichment record directly (bypasses publish)."""
        if entry is None:
            entry = self._make_entry()
        return self.Enrichment.create({
            'entry_id': entry.id,
            'language': language,
            'status': status,
        })

    # ------------------------------------------------------------------ #
    # Basic model tests
    # ------------------------------------------------------------------ #

    def test_enrichment_model_exists(self):
        self.assertIn('language.enrichment', self.env)

    def test_enrichment_field_defaults(self):
        enrichment = self._make_enrichment()
        self.assertEqual(enrichment.status, 'pending')
        self.assertFalse(enrichment.synonyms)
        self.assertFalse(enrichment.antonyms)
        self.assertFalse(enrichment.example_sentences)
        self.assertFalse(enrichment.explanation)
        self.assertFalse(enrichment.job_id)

    def test_entry_has_enrichment_ids_field(self):
        entry = self._make_entry()
        self.assertIsNotNone(entry.enrichment_ids)

    def test_unique_entry_language_constraint(self):
        entry = self._make_entry()
        self._make_enrichment(entry=entry, language='en')
        with self.assertRaises(Exception):
            # Second record for same (entry, language) must fail
            self.env['language.enrichment'].sudo().create({
                'entry_id': entry.id,
                'language': 'en',
                'status': 'pending',
            })

    # ------------------------------------------------------------------ #
    # Enqueue / publish tests
    # ------------------------------------------------------------------ #

    def test_enqueue_single_creates_record_and_publishes(self):
        entry = self._make_entry()
        with self._patch_publish() as mock_pub:
            enrichment = self.env['language.enrichment'].sudo()._enqueue_single(entry, 'en')
        self.assertTrue(enrichment.id)
        self.assertEqual(enrichment.status, 'processing')
        self.assertTrue(enrichment.job_id)
        mock_pub.assert_called_once()
        call_args = mock_pub.call_args
        self.assertEqual(call_args[0][0], 'enrichment.requested')

    def test_enqueue_single_publishes_correct_payload(self):
        entry = self._make_entry(source_text='hello', source_language='en')
        with self._patch_publish() as mock_pub:
            self.Enrichment._enqueue_single(entry, 'en')
        payload = mock_pub.call_args[0][1]
        self.assertEqual(payload['source_text'], 'hello')
        self.assertEqual(payload['source_language'], 'en')
        self.assertEqual(payload['language'], 'en')
        self.assertEqual(payload['entry_id'], entry.id)

    def test_enqueue_single_reuses_existing_record(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='failed')
        with self._patch_publish():
            result = self.env['language.enrichment'].sudo()._enqueue_single(entry, 'en')
        self.assertEqual(result.id, enrichment.id)
        self.assertEqual(result.status, 'processing')

    # ------------------------------------------------------------------ #
    # State machine tests
    # ------------------------------------------------------------------ #

    def test_handle_completed_updates_record(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='processing')
        enrichment.sudo().write({'job_id': 'test-job-completed-1'})

        self.Enrichment._handle_completed(
            'test-job-completed-1',
            {
                'synonyms': ['syn1', 'syn2'],
                'antonyms': ['ant1'],
                'example_sentences': ['Example one.', 'Example two.'],
                'explanation': 'A test explanation.',
            },
        )
        enrichment.invalidate_recordset()
        self.assertEqual(enrichment.status, 'completed')
        self.assertEqual(json.loads(enrichment.synonyms), ['syn1', 'syn2'])
        self.assertEqual(json.loads(enrichment.antonyms), ['ant1'])
        self.assertEqual(enrichment.explanation, 'A test explanation.')

    def test_handle_failed_updates_record(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='processing')
        enrichment.sudo().write({'job_id': 'test-job-failed-1'})

        self.Enrichment._handle_failed(
            'test-job-failed-1',
            {'error': 'LLM timeout'},
        )
        enrichment.invalidate_recordset()
        self.assertEqual(enrichment.status, 'failed')
        self.assertEqual(enrichment.error_message, 'LLM timeout')

    def test_handle_completed_idempotent(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='completed')
        enrichment.sudo().write({
            'job_id': 'test-idempotent-completed',
            'synonyms': '["original"]',
        })

        # Second delivery of completed — must be no-op
        self.Enrichment._handle_completed(
            'test-idempotent-completed',
            {'synonyms': ['overwrite_attempt']},
        )
        enrichment.invalidate_recordset()
        self.assertEqual(json.loads(enrichment.synonyms), ['original'])

    def test_handle_failed_idempotent(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='failed')
        enrichment.sudo().write({
            'job_id': 'test-idempotent-failed',
            'error_message': 'original error',
        })

        self.Enrichment._handle_failed(
            'test-idempotent-failed',
            {'error': 'new error attempt'},
        )
        enrichment.invalidate_recordset()
        self.assertEqual(enrichment.error_message, 'original error')

    def test_handle_unknown_job_id_is_noop(self):
        # Should not raise, just log a warning
        self.Enrichment._handle_completed('unknown-job-xyz', {})
        self.Enrichment._handle_failed('unknown-job-xyz', {})

    # ------------------------------------------------------------------ #
    # Retry tests
    # ------------------------------------------------------------------ #

    def test_action_retry_raises_on_completed(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='completed')
        with self.assertRaises(UserError):
            enrichment.action_retry()

    def test_action_retry_re_enqueues_failed(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='failed')
        enrichment.sudo().write({'job_id': 'old-job-id', 'error_message': 'timeout'})

        with self._patch_publish() as mock_pub:
            enrichment.sudo().action_retry()

        enrichment.invalidate_recordset()
        self.assertEqual(enrichment.status, 'processing')
        self.assertNotEqual(enrichment.job_id, 'old-job-id')
        self.assertFalse(enrichment.error_message)
        mock_pub.assert_called_once()

    # ------------------------------------------------------------------ #
    # JSON helper tests
    # ------------------------------------------------------------------ #

    def test_synonyms_list_helper(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='completed')
        enrichment.sudo().write({'synonyms': '["cat", "feline"]'})
        self.assertEqual(enrichment._synonyms_list(), ['cat', 'feline'])

    def test_synonyms_list_empty_on_null(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en')
        self.assertEqual(enrichment._synonyms_list(), [])

    def test_example_sentences_list_helper(self):
        entry = self._make_entry()
        enrichment = self._make_enrichment(entry=entry, language='en', status='completed')
        enrichment.sudo().write({'example_sentences': '["Sentence one.", "Sentence two."]'})
        self.assertEqual(len(enrichment._example_sentences_list()), 2)
