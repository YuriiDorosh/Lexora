from datetime import date, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLanguageReview(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref('language_security.group_language_user')
        cls.user = cls.env['res.users'].sudo().create({
            'name': 'SRS Test User',
            'login': 'srs_test@lexora.test',
            'email': 'srs_test@lexora.test',
            'groups_id': [(6, 0, [cls.group_user.id])],
        })
        cls.Entry = cls.env['language.entry'].sudo()
        cls.Review = cls.env['language.review'].sudo()

        cls.entry = cls.Entry.create({
            'source_text': 'apple',
            'source_language': 'en',
            'owner_id': cls.user.id,
        })

    def _new_card(self):
        return self.Review.create({
            'entry_id': self.entry.id,
            'user_id': self.user.id,
        })

    def _fresh_card(self):
        """Search or create a card, unlinking first so tests are independent."""
        existing = self.Review.search([
            ('user_id', '=', self.user.id),
            ('entry_id', '=', self.entry.id),
        ])
        existing.unlink()
        return self._new_card()

    # ------------------------------------------------------------------ #
    # 1. Default field values
    # ------------------------------------------------------------------ #

    def test_01_default_state_new(self):
        card = self._fresh_card()
        self.assertEqual(card.state, 'new')

    def test_02_default_ef(self):
        card = self._fresh_card()
        self.assertAlmostEqual(card.ease_factor, 2.5)

    def test_03_default_repetitions_zero(self):
        card = self._fresh_card()
        self.assertEqual(card.repetitions, 0)

    # ------------------------------------------------------------------ #
    # 2. UNIQUE constraint
    # ------------------------------------------------------------------ #

    def test_04_unique_constraint(self):
        self._fresh_card()
        with self.assertRaises(Exception):
            self._new_card()

    # ------------------------------------------------------------------ #
    # 3. grade=Again (0)
    # ------------------------------------------------------------------ #

    def test_05_grade_again_resets_repetitions(self):
        card = self._fresh_card()
        card.write({'repetitions': 3, 'interval': 10, 'state': 'review'})
        card.action_register_review(0)
        self.assertEqual(card.repetitions, 0)
        self.assertEqual(card.interval, 1)
        self.assertEqual(card.state, 'learning')

    # ------------------------------------------------------------------ #
    # 4. grade=Hard (1)
    # ------------------------------------------------------------------ #

    def test_06_grade_hard_extends_interval(self):
        card = self._fresh_card()
        card.write({'interval': 5, 'repetitions': 1, 'state': 'learning'})
        card.action_register_review(1)
        self.assertEqual(card.interval, max(1, round(5 * 1.2)))
        self.assertAlmostEqual(card.ease_factor, 2.5 - 0.15, places=4)

    def test_07_grade_hard_does_not_increment_repetitions(self):
        card = self._fresh_card()
        card.write({'repetitions': 2, 'interval': 4})
        before = card.repetitions
        card.action_register_review(1)
        self.assertEqual(card.repetitions, before)

    # ------------------------------------------------------------------ #
    # 5. grade=Good (2)
    # ------------------------------------------------------------------ #

    def test_08_grade_good_increments_repetitions(self):
        card = self._fresh_card()
        card.action_register_review(2)
        self.assertEqual(card.repetitions, 1)
        self.assertEqual(card.interval, 1)
        self.assertEqual(card.state, 'learning')

    def test_09_grade_good_second_rep_graduates(self):
        card = self._fresh_card()
        card.write({'repetitions': 1, 'interval': 1})
        card.action_register_review(2)
        self.assertEqual(card.repetitions, 2)
        self.assertEqual(card.interval, 4)
        self.assertEqual(card.state, 'review')

    def test_10_grade_good_third_rep_uses_ef(self):
        card = self._fresh_card()
        card.write({'repetitions': 2, 'interval': 4, 'ease_factor': 2.5})
        card.action_register_review(2)
        self.assertEqual(card.repetitions, 3)
        self.assertEqual(card.interval, max(1, round(4 * 2.5)))

    # ------------------------------------------------------------------ #
    # 6. grade=Easy (3)
    # ------------------------------------------------------------------ #

    def test_11_grade_easy_inflates_interval(self):
        card = self._fresh_card()
        card.write({'repetitions': 2, 'interval': 4, 'ease_factor': 2.5})
        card.action_register_review(3)
        expected_i = max(1, round(round(4 * 2.5) * 1.3))
        self.assertEqual(card.interval, expected_i)
        self.assertAlmostEqual(card.ease_factor, 2.5 + 0.15, places=4)
        self.assertEqual(card.state, 'review')

    # ------------------------------------------------------------------ #
    # 7. Invalid grade
    # ------------------------------------------------------------------ #

    def test_12_invalid_grade_raises(self):
        card = self._fresh_card()
        with self.assertRaises(ValidationError):
            card.action_register_review(5)

    # ------------------------------------------------------------------ #
    # 8. Stats tracking
    # ------------------------------------------------------------------ #

    def test_13_correct_reviews_incremented_on_good(self):
        card = self._fresh_card()
        card.action_register_review(2)
        self.assertEqual(card.total_reviews, 1)
        self.assertEqual(card.correct_reviews, 1)

    def test_14_correct_reviews_not_incremented_on_again(self):
        card = self._fresh_card()
        card.action_register_review(0)
        self.assertEqual(card.total_reviews, 1)
        self.assertEqual(card.correct_reviews, 0)

    # ------------------------------------------------------------------ #
    # 9. get_due_cards / enqueue_new_entries
    # ------------------------------------------------------------------ #

    def test_15_get_due_cards_returns_overdue(self):
        card = self._fresh_card()
        yesterday = date.today() - timedelta(days=1)
        card.write({'next_review_date': yesterday})
        due = self.Review.get_due_cards(user_id=self.user.id, limit=20)
        self.assertIn(card, due)

    def test_16_get_due_cards_excludes_future(self):
        card = self._fresh_card()
        tomorrow = date.today() + timedelta(days=1)
        card.write({'next_review_date': tomorrow})
        due = self.Review.get_due_cards(user_id=self.user.id, limit=20)
        self.assertNotIn(card, due)

    def test_17_enqueue_new_entries_creates_cards(self):
        # Remove any existing card for this entry
        self.Review.search([
            ('user_id', '=', self.user.id),
            ('entry_id', '=', self.entry.id),
        ]).unlink()
        count = self.Review.enqueue_new_entries(user_id=self.user.id, batch=10)
        self.assertGreaterEqual(count, 1)
        card = self.Review.search([
            ('user_id', '=', self.user.id),
            ('entry_id', '=', self.entry.id),
        ], limit=1)
        self.assertTrue(card)

    def test_18_enqueue_idempotent(self):
        self._fresh_card()  # card already exists
        count = self.Review.enqueue_new_entries(user_id=self.user.id, batch=10)
        # Should not create another card for the same entry
        self.assertEqual(count, 0)

    # ------------------------------------------------------------------ #
    # 10. EF bounds
    # ------------------------------------------------------------------ #

    def test_19_ef_never_below_minimum(self):
        card = self._fresh_card()
        card.write({'ease_factor': 1.31, 'interval': 1})
        # Repeated Hard grades should floor at EF_MIN
        for _ in range(10):
            card.action_register_review(1)
        self.assertGreaterEqual(card.ease_factor, 1.3)

    def test_20_ef_never_above_maximum(self):
        card = self._fresh_card()
        card.write({'ease_factor': 3.49, 'interval': 4, 'repetitions': 2})
        for _ in range(10):
            card.action_register_review(3)
        self.assertLessEqual(card.ease_factor, 3.5)
