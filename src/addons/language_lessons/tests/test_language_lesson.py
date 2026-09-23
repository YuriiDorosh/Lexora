"""ORM tests for language.lesson / language.lesson.item novelty analysis.

Every ``language.entry.create()`` call auto-enqueues translation jobs
(M29), so RabbitMQPublisher.publish is patched the same way M3's
translation tests do — no real RabbitMQ connection in the test env.
"""

from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

_PUBLISHER_PATH = (
    'odoo.addons.language_core.models.rabbitmq_publisher.RabbitMQPublisher.publish'
)
_REQUESTS_POST_PATH = 'odoo.addons.language_lessons.models.language_lesson.requests.post'


def _patch_publish():
    return patch(_PUBLISHER_PATH, return_value='test-job-id')


class TestLanguageLesson(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'Lesson Test User',
            'login': 'lesson_test_user@lexora.test',
            'email': 'lesson_test_user@lexora.test',
            'groups_id': [(6, 0, [cls.env.ref('language_security.group_language_user').id])],
        })
        cls.env['language.user.profile']._get_or_create_for_user(cls.user)
        cls.Lesson = cls.env['language.lesson'].with_user(cls.user)
        cls.Item = cls.env['language.lesson.item'].sudo()
        cls.Entry = cls.env['language.entry'].with_user(cls.user)
        cls.Review = cls.env['language.review'].sudo()

    def _make_lesson(self, raw_payload, lesson_date='2026-06-01', name='New Lesson'):
        return self.Lesson.create({
            'name': name,
            'user_id': self.user.id,
            'lesson_date': lesson_date,
            'language': 'en',
            'raw_payload': raw_payload,
        })

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    def test_parse_sets_state_and_topic(self):
        lesson = self._make_lesson('Topic: Airports\nVocab:\n- gate')
        lesson.action_parse()
        self.assertEqual(lesson.state, 'parsed')
        self.assertEqual(lesson.name, 'Airports')
        self.assertEqual(len(lesson.item_ids), 1)

    def test_reparse_replaces_items_not_duplicates(self):
        lesson = self._make_lesson('Vocab:\n- gate\n- runway')
        lesson.action_parse()
        self.assertEqual(len(lesson.item_ids), 2)
        lesson.raw_payload = 'Vocab:\n- gate'
        lesson.action_reparse()
        self.assertEqual(len(lesson.item_ids), 1)
        self.assertEqual(lesson.state, 'parsed')

    # ------------------------------------------------------------------
    # Novelty: new
    # ------------------------------------------------------------------

    def test_new_vocab_creates_entry(self):
        lesson = self._make_lesson('Vocab:\n- ephemeral')
        lesson.action_parse()
        with _patch_publish():
            lesson.action_analyze_novelty()
        item = lesson.item_ids[0]
        self.assertEqual(item.novelty, 'new')
        self.assertEqual(item.seen_source, 'none')
        self.assertTrue(item.entry_id)
        self.assertEqual(item.entry_id.source_text, 'ephemeral')
        self.assertEqual(item.entry_id.created_from, 'lesson_import')
        self.assertEqual(item.emphasis_weight, 3)
        self.assertEqual(lesson.new_count, 1)

    # ------------------------------------------------------------------
    # Novelty: seen (via existing dictionary entry, no review card)
    # ------------------------------------------------------------------

    def test_seen_via_existing_dictionary_entry(self):
        with _patch_publish():
            self.Entry.create({
                'type': 'word',
                'source_text': 'apple',
                'source_language': 'en',
                'owner_id': self.user.id,
            })
        lesson = self._make_lesson('Vocab:\n- apple')
        lesson.action_parse()
        with _patch_publish():
            lesson.action_analyze_novelty()
        item = lesson.item_ids[0]
        self.assertEqual(item.novelty, 'seen')
        self.assertEqual(item.seen_source, 'vocab')
        self.assertEqual(item.emphasis_weight, 2)
        # No duplicate entry created.
        self.assertEqual(
            self.env['language.entry'].search_count([
                ('owner_id', '=', self.user.id), ('normalized_text', '=', 'apple'),
            ]),
            1,
        )

    # ------------------------------------------------------------------
    # Novelty: known (review card in 'review' state)
    # ------------------------------------------------------------------

    def test_known_via_review_state(self):
        with _patch_publish():
            entry = self.Entry.create({
                'type': 'word',
                'source_text': 'banana',
                'source_language': 'en',
                'owner_id': self.user.id,
            })
        self.Review.create({'entry_id': entry.id, 'user_id': self.user.id, 'state': 'review'})
        lesson = self._make_lesson('Vocab:\n- banana')
        lesson.action_parse()
        with _patch_publish():
            lesson.action_analyze_novelty()
        item = lesson.item_ids[0]
        self.assertEqual(item.novelty, 'known')
        self.assertEqual(item.srs_state_at_import, 'review')
        self.assertEqual(item.emphasis_weight, 1)
        self.assertEqual(lesson.known_count, 1)

    def test_seen_not_known_when_review_state_is_learning(self):
        with _patch_publish():
            entry = self.Entry.create({
                'type': 'word',
                'source_text': 'cherry',
                'source_language': 'en',
                'owner_id': self.user.id,
            })
        self.Review.create({'entry_id': entry.id, 'user_id': self.user.id, 'state': 'learning'})
        lesson = self._make_lesson('Vocab:\n- cherry')
        lesson.action_parse()
        with _patch_publish():
            lesson.action_analyze_novelty()
        self.assertEqual(lesson.item_ids[0].novelty, 'seen')

    # ------------------------------------------------------------------
    # Novelty: seen via a previous lesson (no active dictionary entry)
    # ------------------------------------------------------------------

    def test_seen_via_previous_lesson_only(self):
        earlier_lesson = self._make_lesson('Notes:\n- placeholder', lesson_date='2026-05-01')
        # Simulate a historical lesson item without going through analyze
        # (e.g. its entry was later archived/deleted independently).
        self.Item.create({
            'lesson_id': earlier_lesson.id,
            'item_type': 'vocab',
            'text': 'itinerary',
        })
        later_lesson = self._make_lesson('Vocab:\n- itinerary', lesson_date='2026-06-15')
        later_lesson.action_parse()
        with _patch_publish():
            later_lesson.action_analyze_novelty()
        item = later_lesson.item_ids[0]
        self.assertEqual(item.novelty, 'seen')
        self.assertEqual(item.seen_source, 'previous_lesson')
        self.assertEqual(item.first_seen_lesson_id.id, earlier_lesson.id)

    # ------------------------------------------------------------------
    # Longest-match sub-phrase (ADR-038 § 38d, ported from M34)
    # ------------------------------------------------------------------

    def test_longest_match_subphrase(self):
        with _patch_publish():
            self.Entry.create({
                'type': 'phrase',
                'source_text': 'check in',
                'source_language': 'en',
                'owner_id': self.user.id,
            })
        lesson = self._make_lesson('Phrases:\n- to check in at the gate')
        lesson.action_parse()
        with _patch_publish():
            lesson.action_analyze_novelty()
        item = lesson.item_ids[0]
        self.assertEqual(item.novelty, 'seen')
        self.assertEqual(item.entry_id.source_text, 'check in')
        # The whole 6-token phrase must NOT have created a second entry.
        self.assertFalse(
            self.env['language.entry'].search([
                ('owner_id', '=', self.user.id),
                ('normalized_text', '=', 'to check in at the gate'),
            ])
        )

    # ------------------------------------------------------------------
    # Recurring mistakes
    # ------------------------------------------------------------------

    def test_recurring_mistake_detected(self):
        first = self._make_lesson(
            'Mistakes:\n- I go to school yesterday -> I went to school yesterday',
            lesson_date='2026-05-01',
        )
        first.action_parse()
        with _patch_publish():
            first.action_analyze_novelty()
        self.assertFalse(first.item_ids[0].is_recurring_mistake)

        second = self._make_lesson(
            'Mistakes:\n- I go to school yesterday -> I went to school yesterday',
            lesson_date='2026-06-01',
        )
        second.action_parse()
        with _patch_publish():
            second.action_analyze_novelty()
        item = second.item_ids[0]
        self.assertTrue(item.is_recurring_mistake)
        self.assertEqual(item.emphasis_weight, 4)

    # ------------------------------------------------------------------
    # Idempotent re-parse + re-analyze
    # ------------------------------------------------------------------

    def test_reparse_reanalyze_does_not_duplicate_entries(self):
        lesson = self._make_lesson('Vocab:\n- odyssey')
        lesson.action_parse()
        with _patch_publish():
            lesson.action_analyze_novelty()
        self.assertEqual(lesson.item_ids[0].novelty, 'new')

        lesson.action_reparse()
        with _patch_publish():
            lesson.action_analyze_novelty()
        # Second pass finds the entry created by the first pass — no
        # duplicate language.entry, and the item is now classified 'seen'.
        self.assertEqual(lesson.item_ids[0].novelty, 'seen')
        self.assertEqual(
            self.env['language.entry'].search_count([
                ('owner_id', '=', self.user.id), ('normalized_text', '=', 'odyssey'),
            ]),
            1,
        )

    # ------------------------------------------------------------------
    # LLM extraction fallback (ADR-038 § 38g) — triggered when the
    # rule-based parser finds zero section markers, i.e. real freeform
    # Preply-canvas text rather than a hand-typed marker-formatted note.
    # ------------------------------------------------------------------

    def test_no_markers_routes_to_llm_extraction(self):
        raw = (
            'Household Items\n'
            'Lesson Objectives\n'
            '• Name common rooms and furniture\n\n'
            'Category | Words\n'
            'Rooms | living room, kitchen, bathroom\n'
        )
        lesson = self._make_lesson(raw)

        fake_response = MagicMock()
        fake_response.content = b'''{
            "status": "ok",
            "topic": "Household Items",
            "items": [
                {"item_type": "vocab", "text": "living room", "translation_hint": null,
                 "corrected_text": null, "context": null},
                {"item_type": "vocab", "text": "kitchen", "translation_hint": null,
                 "corrected_text": null, "context": null},
                {"item_type": "vocab", "text": "bathroom", "translation_hint": null,
                 "corrected_text": null, "context": null}
            ]
        }'''
        fake_response.raise_for_status = lambda: None

        with patch(_REQUESTS_POST_PATH, return_value=fake_response) as mock_post:
            lesson.action_parse()

        mock_post.assert_called_once()
        self.assertEqual(lesson.state, 'parsed')
        self.assertEqual(lesson.parse_method, 'llm')
        self.assertEqual(lesson.name, 'Household Items')
        self.assertEqual(len(lesson.item_ids), 3)
        self.assertSetEqual(
            {i.text for i in lesson.item_ids},
            {'living room', 'kitchen', 'bathroom'},
        )

    def test_markers_present_never_calls_llm(self):
        lesson = self._make_lesson('Vocab:\n- gate')
        with patch(_REQUESTS_POST_PATH) as mock_post:
            lesson.action_parse()
        mock_post.assert_not_called()
        self.assertEqual(lesson.parse_method, 'rule_based')

    def test_llm_extraction_service_down_sets_error_state(self):
        lesson = self._make_lesson('Household Items\nJust some prose, no markers at all here.')
        with patch(_REQUESTS_POST_PATH, side_effect=ConnectionError('boom')):
            lesson.action_parse()
        self.assertEqual(lesson.state, 'error')
        self.assertIn('AI', lesson.error_message)

    def test_llm_extraction_empty_result_sets_error_state(self):
        lesson = self._make_lesson('Some freeform text with no markers whatsoever in it.')
        fake_response = MagicMock()
        fake_response.content = b'{"status": "ok", "topic": null, "items": []}'
        fake_response.raise_for_status = lambda: None
        with patch(_REQUESTS_POST_PATH, return_value=fake_response):
            lesson.action_parse()
        self.assertEqual(lesson.state, 'error')
        self.assertEqual(len(lesson.item_ids), 0)
