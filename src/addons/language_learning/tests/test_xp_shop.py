"""Tests for M11 XP Shop — purchase, effects, inventory."""

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestXpShop(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_lu = cls.env.ref('language_security.group_language_user')

        cls.user = cls.env['res.users'].create({
            'name': 'Shop Tester',
            'login': 'shop_tester@test.com',
            'groups_id': [(6, 0, [group_lu.id])],
        })

        # Ensure profile exists with some XP
        Profile = cls.env['language.user.profile'].sudo()
        cls.profile = Profile.search([('user_id', '=', cls.user.id)], limit=1)
        if not cls.profile:
            cls.profile = Profile.create({'user_id': cls.user.id})
        cls.profile.xp_total = 200

        # Get seeded shop items
        ShopItem = cls.env['language.shop.item'].sudo()
        cls.item_freeze = ShopItem.search([('item_type', '=', 'streak_freeze')], limit=1)
        cls.item_frame = ShopItem.search([('item_type', '=', 'profile_frame')], limit=1)
        cls.item_booster = ShopItem.search([('item_type', '=', 'double_xp')], limit=1)

        if not cls.item_freeze:
            cls.item_freeze = ShopItem.create({
                'name': 'Streak Freeze', 'xp_cost': 50,
                'item_type': 'streak_freeze', 'icon': '🧊',
            })
        if not cls.item_frame:
            cls.item_frame = ShopItem.create({
                'name': 'Profile Frame', 'xp_cost': 100,
                'item_type': 'profile_frame', 'icon': '🖼️',
            })
        if not cls.item_booster:
            cls.item_booster = ShopItem.create({
                'name': 'Double XP', 'xp_cost': 80,
                'item_type': 'double_xp', 'icon': '⚡',
            })

    # ------------------------------------------------------------------
    # Basic purchase
    # ------------------------------------------------------------------

    def test_01_buy_deducts_xp(self):
        self.profile.xp_total = 200
        self.item_freeze.action_buy(self.user.id)
        self.assertEqual(self.profile.xp_total, 150)  # 200 - 50

    def test_02_buy_creates_user_item(self):
        self.profile.xp_total = 200
        UserItem = self.env['language.user.item'].sudo()
        before = UserItem.search_count([('user_id', '=', self.user.id)])
        self.item_freeze.action_buy(self.user.id)
        after = UserItem.search_count([('user_id', '=', self.user.id)])
        self.assertEqual(after, before + 1)

    def test_03_buy_creates_xp_log(self):
        self.profile.xp_total = 200
        XpLog = self.env['language.xp.log'].sudo()
        before = XpLog.search_count([
            ('user_id', '=', self.user.id), ('reason', '=', 'shop_purchase'),
        ])
        self.item_freeze.action_buy(self.user.id)
        after = XpLog.search_count([
            ('user_id', '=', self.user.id), ('reason', '=', 'shop_purchase'),
        ])
        self.assertEqual(after, before + 1)

    def test_04_xp_log_amount_is_negative(self):
        self.profile.xp_total = 200
        XpLog = self.env['language.xp.log'].sudo()
        self.item_freeze.action_buy(self.user.id)
        log = XpLog.search([
            ('user_id', '=', self.user.id), ('reason', '=', 'shop_purchase'),
        ], limit=1, order='id desc')
        self.assertEqual(log.amount, -50)

    # ------------------------------------------------------------------
    # Insufficient XP
    # ------------------------------------------------------------------

    def test_05_buy_raises_on_insufficient_xp(self):
        self.profile.xp_total = 10  # less than 50
        with self.assertRaises(UserError):
            self.item_freeze.action_buy(self.user.id)

    def test_06_insufficient_xp_does_not_deduct(self):
        self.profile.xp_total = 10
        try:
            self.item_freeze.action_buy(self.user.id)
        except UserError:
            pass
        self.assertEqual(self.profile.xp_total, 10)

    # ------------------------------------------------------------------
    # Inventory — get_active_item / consume
    # ------------------------------------------------------------------

    def test_07_get_active_item_returns_owned(self):
        self.profile.xp_total = 200
        self.item_freeze.action_buy(self.user.id)
        UserItem = self.env['language.user.item'].sudo()
        found = UserItem._get_active_item(self.user.id, 'streak_freeze')
        self.assertTrue(found)

    def test_08_get_active_item_returns_empty_when_none(self):
        UserItem = self.env['language.user.item'].sudo()
        # Mark all freeze items consumed first
        existing = UserItem.search([
            ('user_id', '=', self.user.id),
            ('item_type', '=', 'streak_freeze'),
            ('is_consumed', '=', False),
        ])
        existing.write({'is_consumed': True, 'quantity': 0})
        result = UserItem._get_active_item(self.user.id, 'streak_freeze')
        self.assertFalse(result)

    def test_09_consume_decrements_quantity(self):
        self.profile.xp_total = 500
        item1 = self.item_freeze.action_buy(self.user.id)
        item2 = self.item_freeze.action_buy(self.user.id)
        # Artificially merge into one record with quantity=2
        item1.quantity = 2
        item1._consume()
        self.assertEqual(item1.quantity, 1)
        self.assertFalse(item1.is_consumed)

    def test_10_consume_marks_consumed_at_zero(self):
        self.profile.xp_total = 200
        ui = self.item_freeze.action_buy(self.user.id)
        # quantity starts at 1
        ui._consume()
        self.assertTrue(ui.is_consumed)
        self.assertEqual(ui.quantity, 0)

    # ------------------------------------------------------------------
    # Profile frame — purely cosmetic (just verify purchase works)
    # ------------------------------------------------------------------

    def test_11_buy_profile_frame(self):
        self.profile.xp_total = 200
        ui = self.item_frame.action_buy(self.user.id)
        self.assertEqual(ui.item_type, 'profile_frame')
        self.assertEqual(self.profile.xp_total, 100)  # 200 - 100

    # ------------------------------------------------------------------
    # Double XP booster effect
    # ------------------------------------------------------------------

    def test_12_double_xp_booster_doubles_review_xp(self):
        """Buying a double_xp booster and then registering a review should double XP."""
        from ..models.language_user_profile_gamification import XP_BY_GRADE
        self.profile.xp_total = 200
        self.profile.current_streak = 0
        self.profile.last_practice_date = False

        self.item_booster.action_buy(self.user.id)
        xp_before = self.profile.xp_total  # 200 - 80 = 120

        Profile = self.env['language.user.profile'].sudo()
        Profile._update_gamification_for_user(self.user.id, grade=2)  # Good = 10 XP base

        expected_xp = xp_before + XP_BY_GRADE[2] * 2  # doubled
        self.assertEqual(self.profile.xp_total, expected_xp)

        # Booster should be consumed
        UserItem = self.env['language.user.item'].sudo()
        active = UserItem._get_active_item(self.user.id, 'double_xp')
        self.assertFalse(active)

    # ------------------------------------------------------------------
    # Active items filter
    # ------------------------------------------------------------------

    def test_13_inactive_shop_item_not_returned(self):
        ShopItem = self.env['language.shop.item'].sudo()
        inactive = ShopItem.create({
            'name': 'Hidden Item', 'xp_cost': 5,
            'item_type': 'streak_freeze', 'is_active': False,
        })
        active_items = ShopItem.search([('is_active', '=', True)])
        self.assertNotIn(inactive, active_items)
