from odoo.tests.common import TransactionCase


class TestSecurityGroups(TransactionCase):
    """Verify that all three Lexora security groups exist, the implication
    chain is correct, and portal signup auto-assigns Language User."""

    def test_groups_exist(self):
        """All three groups must be defined after module install."""
        env = self.env
        self.assertTrue(env.ref('language_security.group_language_user'))
        self.assertTrue(env.ref('language_security.group_language_moderator'))
        self.assertTrue(env.ref('language_security.group_language_admin'))

    def test_implication_chain(self):
        """Moderator implies User; Admin implies Moderator (and transitively User)."""
        group_user = self.env.ref('language_security.group_language_user')
        group_mod = self.env.ref('language_security.group_language_moderator')
        group_admin = self.env.ref('language_security.group_language_admin')

        self.assertIn(
            group_user, group_mod.implied_ids,
            'group_language_moderator must imply group_language_user',
        )
        self.assertIn(
            group_mod, group_admin.implied_ids,
            'group_language_admin must imply group_language_moderator',
        )

    def test_portal_signup_auto_assignment(self):
        """base.group_portal must imply group_language_user so new portal
        users are automatically Language Users (ADR-004 / SPEC §2)."""
        group_portal = self.env.ref('base.group_portal')
        group_lang_user = self.env.ref('language_security.group_language_user')
        self.assertIn(
            group_lang_user, group_portal.implied_ids,
            'base.group_portal must imply group_language_user for auto-assignment',
        )
