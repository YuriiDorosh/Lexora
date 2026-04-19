"""Tests for language.audio model (M6).

Covers:
- Model creation for all three audio_type values
- UNIQUE constraint enforcement for generated/imported types
- recorded audio updates in-place (last wins — no UNIQUE violation)
- _handle_generation_completed: creates attachment, sets status=completed
- _handle_generation_failed: idempotency guard (no-op if already terminal)
- _handle_transcription_completed: writes transcription field
- _handle_transcription_failed: idempotency guard
- audio_ids One2many relation on language.entry
- _enqueue_tts: reuses completed record (lazy), creates new on first call

RabbitMQ publish is patched out; no real broker required.
"""

import base64
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

_PUBLISHER_PATH = (
    'odoo.addons.language_core.models.rabbitmq_publisher.RabbitMQPublisher.publish'
)

FAKE_MP3_B64 = base64.b64encode(b'ID3' + b'\x00' * 64).decode()


def _patch_publish(return_value='test-job-id'):
    return patch(_PUBLISHER_PATH, return_value=return_value)


class TestLanguageAudio(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = cls.env['res.users'].create({
            'name': 'Audio Test User',
            'login': 'audio_test@lexora.test',
            'email': 'audio_test@lexora.test',
            'groups_id': [(6, 0, [cls.env.ref('language_security.group_language_user').id])],
        })
        cls.Audio = cls.env['language.audio'].sudo()
        cls.Entry = cls.env['language.entry'].sudo()

    def _make_entry(self, text='apple', lang='en'):
        with _patch_publish():
            return self.Entry.create({
                'source_text': text,
                'source_language': lang,
                'type': 'word',
                'owner_id': self.user_a.id,
                'created_from': 'manual',
            })

    # ------------------------------------------------------------------ #
    # Model creation
    # ------------------------------------------------------------------ #

    def test_create_generated_audio(self):
        entry = self._make_entry()
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'generated',
            'language': 'en',
            'status': 'pending',
        })
        self.assertEqual(record.audio_type, 'generated')
        self.assertEqual(record.status, 'pending')
        self.assertFalse(record.transcription)

    def test_create_imported_audio(self):
        entry = self._make_entry('яблуко', 'uk')
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'imported',
            'language': 'uk',
            'status': 'completed',
        })
        self.assertEqual(record.audio_type, 'imported')
        self.assertEqual(record.status, 'completed')

    def test_create_recorded_audio(self):
        entry = self._make_entry()
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'recorded',
            'language': 'en',
            'status': 'completed',
        })
        self.assertEqual(record.audio_type, 'recorded')
        self.assertEqual(record.status, 'completed')

    # ------------------------------------------------------------------ #
    # UNIQUE constraint
    # ------------------------------------------------------------------ #

    def test_unique_generated_constraint(self):
        entry = self._make_entry('dog', 'en')
        self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'generated',
            'language': 'en',
            'status': 'pending',
        })
        with self.assertRaises(Exception):
            self.Audio.create({
                'entry_id': entry.id,
                'audio_type': 'generated',
                'language': 'en',
                'status': 'pending',
            })

    def test_recorded_audio_updates_in_place(self):
        """recorded audio create() should update existing record, not raise UNIQUE."""
        entry = self._make_entry('cat', 'en')
        first = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'recorded',
            'language': 'en',
            'status': 'completed',
        })
        # A second recorded record for the same entry+language should not raise.
        result = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'recorded',
            'language': 'en',
            'status': 'completed',
            'tts_engine': False,
        })
        self.assertIn(first.id, result.ids)

    # ------------------------------------------------------------------ #
    # _handle_generation_completed
    # ------------------------------------------------------------------ #

    def test_handle_generation_completed(self):
        entry = self._make_entry('tree', 'en')
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'generated',
            'language': 'en',
            'status': 'processing',
            'job_id': 'gen-job-001',
        })
        self.Audio._handle_generation_completed('gen-job-001', {
            'audio_b64': FAKE_MP3_B64,
            'tts_engine': 'edge-tts',
            'file_size_bytes': 67,
        })
        record.invalidate_recordset()
        self.assertEqual(record.status, 'completed')
        self.assertEqual(record.tts_engine, 'edge-tts')
        self.assertTrue(record.attachment_id)

    def test_handle_generation_completed_idempotency(self):
        entry = self._make_entry('fish', 'en')
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'generated',
            'language': 'en',
            'status': 'completed',
            'job_id': 'gen-job-002',
        })
        self.Audio._handle_generation_completed('gen-job-002', {'audio_b64': FAKE_MP3_B64})
        record.invalidate_recordset()
        self.assertFalse(record.attachment_id, 'Idempotency: no attachment created on second delivery')

    # ------------------------------------------------------------------ #
    # _handle_generation_failed
    # ------------------------------------------------------------------ #

    def test_handle_generation_failed(self):
        entry = self._make_entry('bird', 'en')
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'generated',
            'language': 'en',
            'status': 'processing',
            'job_id': 'gen-job-003',
        })
        self.Audio._handle_generation_failed('gen-job-003', {'error': 'TTS service timeout'})
        record.invalidate_recordset()
        self.assertEqual(record.status, 'failed')
        self.assertIn('timeout', record.error_message)

    def test_handle_generation_failed_idempotency(self):
        entry = self._make_entry('lion', 'en')
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'generated',
            'language': 'en',
            'status': 'failed',
            'job_id': 'gen-job-004',
            'error_message': 'original error',
        })
        self.Audio._handle_generation_failed('gen-job-004', {'error': 'second delivery'})
        record.invalidate_recordset()
        self.assertEqual(record.error_message, 'original error', 'Idempotency: error not overwritten')

    # ------------------------------------------------------------------ #
    # _handle_transcription_completed / failed
    # ------------------------------------------------------------------ #

    def test_handle_transcription_completed(self):
        entry = self._make_entry('sun', 'en')
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'recorded',
            'language': 'en',
            'status': 'completed',
            'transcription_status': 'processing',
            'transcription_job_id': 'tr-job-001',
        })
        self.Audio._handle_transcription_completed('tr-job-001', {'transcription': 'sun'})
        record.invalidate_recordset()
        self.assertEqual(record.transcription, 'sun')
        self.assertEqual(record.transcription_status, 'completed')

    def test_handle_transcription_failed(self):
        entry = self._make_entry('moon', 'en')
        record = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'recorded',
            'language': 'en',
            'status': 'completed',
            'transcription_status': 'processing',
            'transcription_job_id': 'tr-job-002',
        })
        self.Audio._handle_transcription_failed('tr-job-002', {'error': 'model not ready'})
        record.invalidate_recordset()
        self.assertEqual(record.transcription_status, 'failed')
        self.assertIn('model not ready', record.transcription_error)

    # ------------------------------------------------------------------ #
    # audio_ids on language.entry
    # ------------------------------------------------------------------ #

    def test_audio_ids_relation(self):
        entry = self._make_entry('star', 'en')
        self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'imported',
            'language': 'en',
            'status': 'completed',
        })
        entry.invalidate_recordset()
        self.assertEqual(len(entry.audio_ids), 1)
        self.assertEqual(entry.audio_ids[0].audio_type, 'imported')

    # ------------------------------------------------------------------ #
    # _enqueue_tts
    # ------------------------------------------------------------------ #

    def test_enqueue_tts_creates_record(self):
        entry = self._make_entry('sky', 'en')
        with _patch_publish() as mock_pub:
            record = self.Audio._enqueue_tts(entry, 'en')
        self.assertEqual(record.audio_type, 'generated')
        self.assertEqual(record.language, 'en')
        self.assertEqual(record.status, 'processing')
        mock_pub.assert_called_once()

    def test_enqueue_tts_reuses_completed(self):
        entry = self._make_entry('cloud', 'en')
        existing = self.Audio.create({
            'entry_id': entry.id,
            'audio_type': 'generated',
            'language': 'en',
            'status': 'completed',
            'job_id': 'already-done',
        })
        with _patch_publish() as mock_pub:
            result = self.Audio._enqueue_tts(entry, 'en')
        self.assertEqual(result.id, existing.id)
        mock_pub.assert_not_called()
