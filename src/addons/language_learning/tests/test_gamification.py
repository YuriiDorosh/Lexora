"""Tests for M8 gamification — XP, streaks, levels, leaderboard ordering."""

import math
from datetime import date, timedelta
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

from ..models.language_user_profile_gamification import (
    _xp_to_level,
    _level_progress_pct,
    XP_BY_GRADE,
    LEVEL_CAP,
)


class TestGamificationHelpers(TransactionCase):
    """Unit tests for pure helper functions (no DB required)."""

    # --- _xp_to_level ---

    def test_01_level_at_zero_xp(self):
        self.assertEqual(_xp_to_level(0), 1)

    def test_02_level_boundary_level2(self):
        # Level 2 starts at 50 XP (floor(sqrt(50/50))+1 = 2)
        self.assertEqual(_xp_to_level(49), 1)
        self.assertEqual(_xp_to_level(50), 2)

    def test_03_level_boundary_level3(self):
        # Level 3 starts at 200 XP
        self.assertEqual(_xp_to_level(199), 2)
        self.assertEqual(_xp_to_level(200), 3)

    def test_04_level_boundary_level10(self):
        # Level 10 starts at 50*(10-1)^2 = 4050
        self.assertEqual(_xp_to_level(4049), 9)
        self.assertEqual(_xp_to_level(4050), 10)

    def test_05_level_cap_at_20(self):
        self.assertEqual(_xp_to_level(18050), 20)
        self.assertEqual(_xp_to_level(999999), 20)

    def test_06_level_negative_xp_treated_as_zero(self):
        self.assertEqual(_xp_to_level(-100), 1)

    # --- _level_progress_pct ---

    def test_07_progress_at_level_floor(self):
        # Exactly at level 2 floor (50 XP) → 0 %
        self.assertEqual(_level_progress_pct(50), 0)

    def test_08_progress_halfway(self):
        # L2 band: 50–200, midpoint 125 → 50 %
        pct = _level_progress_pct(125)
        self.assertAlmostEqual(pct, 50, delta=2)

    def test_09_progress_at_cap_is_100(self):
        self.assertEqual(_level_progress_pct(18050), 100)
        self.assertEqual(_level_progress_pct(999999), 100)

    # --- XP_BY_GRADE ---

    def test_10_xp_by_grade_values(self):
        self.assertEqual(XP_BY_GRADE[0], 0)
        self.assertEqual(XP_BY_GRADE[1], 5)
        self.assertEqual(XP_BY_GRADE[2], 10)
        self.assertEqual(XP_BY_GRADE[3], 15)


class TestGamificationModel(TransactionCase):
    """Integration tests against the DB — exercise _update_gamification_for_user."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Profile = cls.env['language.user.profile'].sudo()

        # Create a dedicated test user
        cls.user = cls.env['res.users'].sudo().create({
            'name': 'Gamification Test User',
            'login': 'gamification_test@lexora.test',
            'email': 'gamification_test@lexora.test',
            'groups_id': [(4, cls.env.ref('base.group_portal').id)],
        })

    def _profile(self):
        return self.Profile._get_or_create_for_user(self.user.id)

    def _reset_profile(self):
        """Wipe gamification state for a clean slate between tests."""
        self._profile().write({
            'xp_total': 0,
            'current_streak': 0,
            'longest_streak': 0,
            'last_practice_date': False,
        })

    def setUp(self):
        super().setUp()
        self._reset_profile()

    # --- XP accumulation ---

    def test_11_again_awards_zero_xp(self):
        self.Profile._update_gamification_for_user(self.user.id, 0)
        self.assertEqual(self._profile().xp_total, 0)

    def test_12_hard_awards_5_xp(self):
        self.Profile._update_gamification_for_user(self.user.id, 1)
        self.assertEqual(self._profile().xp_total, 5)

    def test_13_good_awards_10_xp(self):
        self.Profile._update_gamification_for_user(self.user.id, 2)
        self.assertEqual(self._profile().xp_total, 10)

    def test_14_easy_awards_15_xp(self):
        self.Profile._update_gamification_for_user(self.user.id, 3)
        self.assertEqual(self._profile().xp_total, 15)

    # --- Streak logic ---

    def test_15_first_practice_sets_streak_to_1(self):
        self.Profile._update_gamification_for_user(self.user.id, 2)
        p = self._profile()
        self.assertEqual(p.current_streak, 1)
        self.assertEqual(p.last_practice_date, date.today())

    def test_16_same_day_second_review_does_not_increment_streak(self):
        # First call
        self.Profile._update_gamification_for_user(self.user.id, 2)
        # Second call same day
        self.Profile._update_gamification_for_user(self.user.id, 3)
        self.assertEqual(self._profile().current_streak, 1)

    def test_17_same_day_xp_still_accumulates(self):
        self.Profile._update_gamification_for_user(self.user.id, 2)  # +10
        self.Profile._update_gamification_for_user(self.user.id, 3)  # +15
        self.assertEqual(self._profile().xp_total, 25)

    def test_18_consecutive_day_extends_streak(self):
        yesterday = date.today() - timedelta(days=1)
        self._profile().write({'last_practice_date': yesterday, 'current_streak': 3})
        self.Profile._update_gamification_for_user(self.user.id, 2)
        p = self._profile()
        self.assertEqual(p.current_streak, 4)

    def test_19_gap_resets_streak_to_1(self):
        two_days_ago = date.today() - timedelta(days=2)
        self._profile().write({'last_practice_date': two_days_ago, 'current_streak': 10})
        self.Profile._update_gamification_for_user(self.user.id, 2)
        self.assertEqual(self._profile().current_streak, 1)

    def test_20_longest_streak_updates_on_new_high(self):
        yesterday = date.today() - timedelta(days=1)
        self._profile().write({
            'last_practice_date': yesterday,
            'current_streak': 5,
            'longest_streak': 5,
        })
        self.Profile._update_gamification_for_user(self.user.id, 2)
        p = self._profile()
        self.assertEqual(p.current_streak, 6)
        self.assertEqual(p.longest_streak, 6)

    def test_21_longest_streak_not_decreased(self):
        yesterday = date.today() - timedelta(days=1)
        self._profile().write({
            'last_practice_date': yesterday,
            'current_streak': 3,
            'longest_streak': 50,  # historic high
        })
        self.Profile._update_gamification_for_user(self.user.id, 2)
        self.assertEqual(self._profile().longest_streak, 50)

    # --- Level computation (stored field) ---

    def test_22_level_stored_updates_when_xp_changes(self):
        p = self._profile()
        p.write({'xp_total': 50})
        self.assertEqual(p.level, 2)

    def test_23_level_progress_pct_at_50_xp(self):
        p = self._profile()
        p.write({'xp_total': 50})
        self.assertEqual(p.level_progress_pct, 0)

    # --- Leaderboard ordering ---

    def test_24_profiles_ordered_by_xp_desc(self):
        # Create a second user with more XP
        user2 = self.env['res.users'].sudo().create({
            'name': 'Leaderboard User B',
            'login': 'lb_user_b@lexora.test',
            'email': 'lb_user_b@lexora.test',
            'groups_id': [(4, self.env.ref('base.group_portal').id)],
        })
        profile_b = self.Profile._get_or_create_for_user(user2.id)

        self._profile().write({'xp_total': 100})
        profile_b.write({'xp_total': 500})

        top = self.Profile.search(
            [('xp_total', '>', 0)],
            order='xp_total desc',
            limit=10,
        )
        first_xp = top[0].xp_total
        last_xp = top[-1].xp_total
        self.assertGreaterEqual(first_xp, last_xp)
        self.assertEqual(top[0].xp_total, 500)
