"""Tests for language.duel and language.duel.line models (M9)."""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


from unittest.mock import patch

_PUBLISHER_PATH = (
    'odoo.addons.language_core.models.rabbitmq_publisher.RabbitMQPublisher.publish'
)


def _patch_publish():
    """Context manager: suppress RabbitMQ publish during tests."""
    return patch(_PUBLISHER_PATH, return_value='test-job-id')


class TestLanguageDuel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group = cls.env.ref('language_security.group_language_user')

        cls.user_a = cls.env['res.users'].sudo().create({
            'name': 'Duel User A',
            'login': 'duel_a@lexora.test',
            'email': 'duel_a@lexora.test',
            'groups_id': [(6, 0, [group.id])],
        })
        cls.user_b = cls.env['res.users'].sudo().create({
            'name': 'Duel User B',
            'login': 'duel_b@lexora.test',
            'email': 'duel_b@lexora.test',
            'groups_id': [(6, 0, [group.id])],
        })

        Entry = cls.env['language.entry'].sudo()
        Translation = cls.env['language.translation'].sudo()

        # Create ≥10 pvp_eligible entries for user_a in English
        cls.entries_a = []
        for i in range(12):
            with _patch_publish():
                e = Entry.create({
                    'source_text': f'word_{i}_a',
                    'source_language': 'en',
                    'owner_id': cls.user_a.id,
                })
            # Mark a translation completed so pvp_eligible=True
            tr = Translation.search([
                ('entry_id', '=', e.id), ('target_language', '=', 'uk')
            ], limit=1)
            if tr:
                tr.write({'status': 'completed', 'translated_text': f'слово_{i}'})
            else:
                Translation.create({
                    'entry_id': e.id,
                    'target_language': 'uk',
                    'translated_text': f'слово_{i}',
                    'status': 'completed',
                })
            e.invalidate_recordset()
            cls.entries_a.append(e)

        # Create ≥10 pvp_eligible entries for user_b in English
        cls.entries_b = []
        for i in range(12):
            with _patch_publish():
                e = Entry.create({
                    'source_text': f'word_{i}_b',
                    'source_language': 'en',
                    'owner_id': cls.user_b.id,
                })
            tr = Translation.search([
                ('entry_id', '=', e.id), ('target_language', '=', 'uk')
            ], limit=1)
            if tr:
                tr.write({'status': 'completed', 'translated_text': f'слово_б_{i}'})
            else:
                Translation.create({
                    'entry_id': e.id,
                    'target_language': 'uk',
                    'translated_text': f'слово_б_{i}',
                    'status': 'completed',
                })
            e.invalidate_recordset()
            cls.entries_b.append(e)

        cls.Duel = cls.env['language.duel'].sudo()
        cls.Line = cls.env['language.duel.line'].sudo()

    def _make_duel(self, state='open', rounds=5):
        return self.Duel.create({
            'challenger_id': self.user_a.id,
            'practice_language': 'en',
            'native_language': 'uk',
            'state': state,
            'rounds_total': rounds,
            'xp_staked': 10,
        })

    # ------------------------------------------------------------------ #
    # 1. Duel creation
    # ------------------------------------------------------------------ #

    def test_01_duel_created_open(self):
        duel = self._make_duel()
        self.assertEqual(duel.state, 'open')
        self.assertFalse(duel.opponent_id)

    def test_02_default_xp_staked(self):
        duel = self._make_duel()
        self.assertEqual(duel.xp_staked, 10)

    def test_03_default_scores_zero(self):
        duel = self._make_duel()
        self.assertEqual(duel.challenger_score, 0)
        self.assertEqual(duel.opponent_score, 0)

    # ------------------------------------------------------------------ #
    # 2. Join state transition
    # ------------------------------------------------------------------ #

    def test_04_join_transitions_to_ongoing(self):
        duel = self._make_duel()
        duel.action_join(self.user_b.id)
        self.assertEqual(duel.state, 'ongoing')
        self.assertEqual(duel.opponent_id.id, self.user_b.id)
        self.assertTrue(duel.start_date)

    def test_05_join_own_challenge_raises(self):
        duel = self._make_duel()
        with self.assertRaises(UserError):
            duel.action_join(self.user_a.id)

    def test_06_join_non_open_challenge_raises(self):
        duel = self._make_duel(state='open')
        duel.action_join(self.user_b.id)  # now ongoing
        user_c = self.env['res.users'].sudo().create({
            'name': 'User C', 'login': 'duel_c@lexora.test',
            'email': 'duel_c@lexora.test',
            'groups_id': [(6, 0, [self.env.ref('language_security.group_language_user').id])],
        })
        with self.assertRaises(UserError):
            duel.action_join(user_c.id)

    # ------------------------------------------------------------------ #
    # 3. Min-entries gate
    # ------------------------------------------------------------------ #

    def test_07_min_entries_gate_passes_with_enough(self):
        duel = self._make_duel()
        # user_a has 12 eligible entries — should not raise
        duel._check_min_entries(self.user_a.id)

    def test_08_min_entries_gate_raises_with_zero(self):
        fresh_user = self.env['res.users'].sudo().create({
            'name': 'Empty User', 'login': 'empty@lexora.test',
            'email': 'empty@lexora.test',
            'groups_id': [(6, 0, [self.env.ref('language_security.group_language_user').id])],
        })
        duel = self._make_duel()
        with self.assertRaises(UserError):
            duel._check_min_entries(fresh_user.id)

    # ------------------------------------------------------------------ #
    # 4. Eligible entry selection
    # ------------------------------------------------------------------ #

    def test_09_eligible_entries_count(self):
        duel = self._make_duel()
        entries = duel._get_eligible_entries(self.user_a.id)
        self.assertGreaterEqual(len(entries), 10)

    def test_10_eligible_entries_all_pvp_eligible(self):
        duel = self._make_duel()
        entries = duel._get_eligible_entries(self.user_a.id)
        self.assertTrue(all(e.pvp_eligible for e in entries))

    def test_11_select_round_entries_respects_n(self):
        duel = self._make_duel()
        sample = duel._select_round_entries(self.user_a.id, 5)
        self.assertLessEqual(len(sample), 5)
        self.assertGreater(len(sample), 0)

    # ------------------------------------------------------------------ #
    # 5. Duel line creation
    # ------------------------------------------------------------------ #

    def test_12_duel_line_created(self):
        duel = self._make_duel(state='open')
        duel.action_join(self.user_b.id)
        entry = self.entries_a[0]
        line = self.Line.create({
            'duel_id': duel.id,
            'player_id': self.user_a.id,
            'entry_id': entry.id,
            'round_number': 1,
            'correct': True,
            'answer_given': 'слово_0',
        })
        self.assertTrue(line.correct)
        self.assertEqual(line.round_number, 1)

    def test_13_rounds_submitted_by(self):
        duel = self._make_duel(state='open')
        duel.action_join(self.user_b.id)
        self.assertEqual(duel._rounds_submitted_by(self.user_a.id), 0)
        self.Line.create({
            'duel_id': duel.id, 'player_id': self.user_a.id,
            'entry_id': self.entries_a[0].id, 'round_number': 1,
        })
        self.assertEqual(duel._rounds_submitted_by(self.user_a.id), 1)

    # ------------------------------------------------------------------ #
    # 6. Finish duel + score tally
    # ------------------------------------------------------------------ #

    def test_14_finish_duel_challenger_wins(self):
        duel = self._make_duel(state='open', rounds=3)
        duel.action_join(self.user_b.id)
        # Challenger: 3 correct, Opponent: 1 correct
        for i in range(3):
            self.Line.create({
                'duel_id': duel.id, 'player_id': self.user_a.id,
                'entry_id': self.entries_a[i].id, 'round_number': i + 1,
                'correct': True,
            })
        for i in range(3):
            self.Line.create({
                'duel_id': duel.id, 'player_id': self.user_b.id,
                'entry_id': self.entries_b[i].id, 'round_number': i + 1,
                'correct': i == 0,  # only first round correct
            })
        duel.action_finish_duel()
        self.assertEqual(duel.state, 'finished')
        self.assertEqual(duel.winner_id.id, self.user_a.id)
        self.assertEqual(duel.challenger_score, 3)
        self.assertEqual(duel.opponent_score, 1)
        self.assertTrue(duel.end_date)

    def test_15_finish_duel_draw(self):
        duel = self._make_duel(state='open', rounds=2)
        duel.action_join(self.user_b.id)
        for i in range(2):
            self.Line.create({
                'duel_id': duel.id, 'player_id': self.user_a.id,
                'entry_id': self.entries_a[i].id, 'round_number': i + 1,
                'correct': True,
            })
            self.Line.create({
                'duel_id': duel.id, 'player_id': self.user_b.id,
                'entry_id': self.entries_b[i].id, 'round_number': i + 1,
                'correct': True,
            })
        duel.action_finish_duel()
        self.assertEqual(duel.state, 'finished')
        self.assertFalse(duel.winner_id)  # draw

    def test_16_finish_duel_is_idempotent(self):
        duel = self._make_duel(state='open', rounds=1)
        duel.action_join(self.user_b.id)
        self.Line.create({
            'duel_id': duel.id, 'player_id': self.user_a.id,
            'entry_id': self.entries_a[0].id, 'round_number': 1, 'correct': True,
        })
        duel.action_finish_duel()
        first_winner = duel.winner_id
        duel.action_finish_duel()  # second call — should be no-op
        self.assertEqual(duel.winner_id, first_winner)
