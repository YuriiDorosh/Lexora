"""Tests for language.translation model (M3).

Covers:
- Model creation and field defaults
- Status state machine (pending → processing → completed / failed)
- Idempotency: duplicate job_id delivery is a no-op
- _enqueue_translations called on entry.create (integration, no real RabbitMQ)
- pvp_eligible computed from translation status
- action_retry resets status to pending and re-enqueues

RabbitMQ is not available in the test environment; we patch the publisher
so publish calls are silently swallowed.

Note: creating an entry auto-enqueues translations for the user's learning
languages (uk → en).  Tests that need a specific translation record use the
auto-created one from entry.translation_ids rather than creating a second
(which would violate the unique constraint).
"""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

_PUBLISHER_PATH = (
    'odoo.addons.language_core.models.rabbitmq_publisher.RabbitMQPublisher.publish'
)


def _patch_publish(return_value='test-job-id'):
    return patch(_PUBLISHER_PATH, return_value=return_value)


class TestLanguageTranslation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = cls.env['res.users'].create({
            'name': 'Trans Test User A',
            'login': 'trans_test_a@lexora.test',
            'email': 'trans_test_a@lexora.test',
            'groups_id': [(6, 0, [cls.env.ref('language_security.group_language_user').id])],
        })
        # user_a: native=uk, learning=[en]
        cls.profile = cls.env['language.user.profile']._get_or_create_for_user(cls.user_a)
        lang_en = cls.env['language.lang'].search([('code', '=', 'en')], limit=1)
        cls.profile.sudo().write({
            'native_language': 'uk',
            'learning_languages': [(4, lang_en.id)],
        })

        cls.Entry = cls.env['language.entry'].sudo()
        cls.Translation = cls.env['language.translation'].sudo()

    def _make_entry(self, source_text='яблуко', source_language='uk'):
        """Create an entry with RabbitMQ publish patched out.

        Creating a uk-source entry auto-enqueues an 'en' translation record.
        """
        with _patch_publish():
            return self.Entry.create({
                'source_text': source_text,
                'source_language': source_language,
                'owner_id': self.user_a.id,
            })

    def _get_auto_translation(self, entry):
        """Return the auto-enqueued translation (en) for a uk entry."""
        return self.Translation.search([
            ('entry_id', '=', entry.id),
            ('target_language', '=', 'en'),
        ], limit=1)

    # ------------------------------------------------------------------ #
    # Model basics
    # ------------------------------------------------------------------ #

    def test_translation_model_exists(self):
        """language.translation model is accessible."""
        self.assertTrue(self.Translation._name == 'language.translation')

    def test_translation_auto_created_on_entry(self):
        """Creating a uk entry auto-creates an 'en' translation record."""
        entry = self._make_entry('слово')
        trans = self._get_auto_translation(entry)
        self.assertTrue(trans, 'Auto translation record should be created')
        self.assertEqual(trans.target_language, 'en')
        self.assertIn(trans.status, ('pending', 'processing'))

    def test_translation_field_defaults(self):
        """Auto-created translation has expected default field values."""
        entry = self._make_entry('поле')
        trans = self._get_auto_translation(entry)
        self.assertFalse(trans.translated_text)
        self.assertFalse(trans.error_message)
        self.assertTrue(trans.job_id, 'job_id should be set after enqueue')

    def test_unique_entry_target_constraint(self):
        """Cannot have two translation records for the same entry+target_language."""
        entry = self._make_entry('унікальне')
        # Auto-created en translation already exists; trying to create another must fail
        with self.assertRaises(Exception):
            self.Translation.create({
                'entry_id': entry.id,
                'target_language': 'en',
            })

    # ------------------------------------------------------------------ #
    # Status state machine — using auto-created translation
    # ------------------------------------------------------------------ #

    def test_status_pending_to_processing_to_completed(self):
        entry = self._make_entry('тест_завершення')
        trans = self._get_auto_translation(entry)
        # Simulate processing completion
        trans.write({'status': 'processing'})
        self.assertEqual(trans.status, 'processing')
        trans.write({'status': 'completed', 'translated_text': 'test_completion'})
        self.assertEqual(trans.status, 'completed')
        self.assertEqual(trans.translated_text, 'test_completion')

    def test_status_to_failed(self):
        entry = self._make_entry('тест_помилки')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'failed', 'error_message': 'Argos unavailable'})
        self.assertEqual(trans.status, 'failed')
        self.assertEqual(trans.error_message, 'Argos unavailable')

    # ------------------------------------------------------------------ #
    # Idempotency (_handle_completed and _handle_failed)
    # ------------------------------------------------------------------ #

    def test_handle_completed_idempotent(self):
        """Duplicate delivery of translation.completed is a no-op."""
        entry = self._make_entry('ідемпотентне')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'completed', 'translated_text': 'original', 'job_id': 'idem-job-1'})

        # Second delivery of the same job_id must not overwrite the result
        self.Translation._handle_completed('idem-job-1', {'translated_text': 'overwrite'})
        trans.invalidate_recordset()
        self.assertEqual(trans.translated_text, 'original', 'Completed record must not be overwritten')

    def test_handle_failed_idempotent(self):
        """Duplicate delivery of translation.failed is a no-op."""
        entry = self._make_entry('невдале')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'failed', 'error_message': 'first error', 'job_id': 'idem-job-2'})

        self.Translation._handle_failed('idem-job-2', {'error': 'second error'})
        trans.invalidate_recordset()
        self.assertEqual(trans.error_message, 'first error', 'Failed record must not be overwritten')

    def test_handle_unknown_job_id_is_noop(self):
        """Unknown job_id in result events is silently ignored (just logs warning)."""
        # Should not raise
        self.Translation._handle_completed('unknown-job-id-xyz', {'translated_text': 'hello'})
        self.Translation._handle_failed('unknown-job-id-xyz', {'error': 'oops'})

    def test_handle_completed_updates_record(self):
        """_handle_completed transitions a processing record to completed."""
        entry = self._make_entry('оновлення')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'processing', 'job_id': 'update-job-1'})

        self.Translation._handle_completed('update-job-1', {'translated_text': 'update'})
        trans.invalidate_recordset()
        self.assertEqual(trans.status, 'completed')
        self.assertEqual(trans.translated_text, 'update')

    def test_handle_failed_updates_record(self):
        """_handle_failed transitions a processing record to failed."""
        entry = self._make_entry('збій')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'processing', 'job_id': 'fail-job-1'})

        self.Translation._handle_failed('fail-job-1', {'error': 'timeout'})
        trans.invalidate_recordset()
        self.assertEqual(trans.status, 'failed')
        self.assertEqual(trans.error_message, 'timeout')

    # ------------------------------------------------------------------ #
    # Auto-enqueue on entry.create
    # ------------------------------------------------------------------ #

    def test_enqueue_on_entry_create_calls_publish(self):
        """Creating an entry calls RabbitMQ publish for each learning language."""
        with _patch_publish(return_value='auto-job-id') as mock_publish:
            self.Entry.create({
                'source_text': 'автомобіль',
                'source_language': 'uk',
                'owner_id': self.user_a.id,
            })
            self.assertTrue(
                mock_publish.called,
                'RabbitMQ publish must be called when creating an entry with learning languages',
            )

    def test_no_enqueue_when_source_matches_learning_language(self):
        """No translation is enqueued when source language equals a learning language."""
        # user_a learning = [en]; create an English source entry → no en→en translation
        with _patch_publish() as mock_publish:
            entry = self.Entry.create({
                'source_text': 'apple',
                'source_language': 'en',
                'owner_id': self.user_a.id,
            })
            # publish should NOT be called (no valid target language)
            self.assertFalse(mock_publish.called, 'Should not publish en→en translation')
        trans = self.Translation.search([('entry_id', '=', entry.id)])
        self.assertFalse(trans, 'Should not create en→en translation record')

    # ------------------------------------------------------------------ #
    # pvp_eligible computed field
    # ------------------------------------------------------------------ #

    def test_pvp_eligible_false_without_completed_translation(self):
        """pvp_eligible is False when all translations are processing/pending."""
        entry = self._make_entry('pvp_test')
        # Auto-created translation is in 'processing', not 'completed'
        self.assertFalse(entry.pvp_eligible)

    def test_pvp_eligible_true_when_translation_completed(self):
        """pvp_eligible becomes True when at least one translation is completed."""
        entry = self._make_entry('pvp_done')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'completed', 'translated_text': 'done'})
        entry.invalidate_recordset()
        self.assertTrue(entry.pvp_eligible)

    def test_pvp_eligible_false_when_translation_failed(self):
        """pvp_eligible stays False if the only translation is failed."""
        entry = self._make_entry('pvp_fail')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'failed', 'error_message': 'err'})
        entry.invalidate_recordset()
        self.assertFalse(entry.pvp_eligible)

    # ------------------------------------------------------------------ #
    # action_retry
    # ------------------------------------------------------------------ #

    def test_action_retry_re_enqueues_failed_translation(self):
        """action_retry resets a failed translation to processing and publishes."""
        entry = self._make_entry('retry')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'failed', 'error_message': 'timeout', 'job_id': 'old-job'})

        with _patch_publish(return_value='new-job-id'):
            trans.action_retry()
        trans.invalidate_recordset()
        self.assertEqual(trans.status, 'processing')
        self.assertFalse(trans.error_message)
        self.assertNotEqual(trans.job_id, 'old-job', 'New job_id should be assigned on retry')

    def test_action_retry_raises_on_completed_translation(self):
        """action_retry raises UserError when translation is already completed."""
        entry = self._make_entry('no_retry')
        trans = self._get_auto_translation(entry)
        trans.write({'status': 'completed', 'translated_text': 'done'})
        with self.assertRaises(UserError):
            trans.action_retry()
