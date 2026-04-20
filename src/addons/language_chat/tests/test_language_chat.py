"""Tests for language_chat — public channels, GC, add_from_chat endpoint."""

from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestChatChannels(TransactionCase):
    """Verify public channel creation and membership."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Channel = cls.env['discuss.channel'].sudo()

    def _get_channel(self, name):
        return self.Channel.search([
            ('name', '=', name),
            ('channel_type', '=', 'channel'),
        ], limit=1)

    def test_01_english_channel_exists(self):
        ch = self._get_channel('english')
        self.assertTrue(ch, "Public #english channel should exist after install")

    def test_02_ukrainian_channel_exists(self):
        ch = self._get_channel('ukrainian')
        self.assertTrue(ch, "Public #ukrainian channel should exist after install")

    def test_03_greek_channel_exists(self):
        ch = self._get_channel('greek')
        self.assertTrue(ch, "Public #greek channel should exist after install")

    def test_04_channels_are_channel_type(self):
        for name in ('english', 'ukrainian', 'greek'):
            ch = self._get_channel(name)
            self.assertTrue(ch, f"Channel '{name}' missing")
            self.assertEqual(ch.channel_type, 'channel')

    def test_05_channel_has_group_public_id(self):
        """Channels should be restricted to Language User group."""
        group = self.env.ref('language_security.group_language_user',
                             raise_if_not_found=False)
        if not group:
            self.skipTest("language_security not installed")
        ch = self._get_channel('english')
        self.assertTrue(ch, "#english channel missing")
        self.assertEqual(ch.group_public_id, group)


class TestChatGC(TransactionCase):
    """Verify _gc_chat_history prunes old messages and leaves recent ones."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Channel = cls.env['discuss.channel'].sudo()
        cls.channel = cls.Channel.search([
            ('name', '=', 'english'),
            ('channel_type', '=', 'channel'),
        ], limit=1)

    def _post_messages(self, count):
        partner = self.env.user.partner_id
        Message = self.env['mail.message'].sudo()
        ids = []
        for i in range(count):
            msg = Message.create({
                'body': f'test message {i}',
                'model': 'discuss.channel',
                'res_id': self.channel.id,
                'message_type': 'comment',
                'subtype_id': self.env.ref('mail.mt_comment').id,
                'author_id': partner.id,
            })
            ids.append(msg.id)
        return ids

    def test_06_gc_does_not_prune_below_limit(self):
        """GC should be a no-op when message count < keep threshold."""
        if not self.channel:
            self.skipTest("#english channel not found")
        Message = self.env['mail.message'].sudo()
        before = Message.search_count([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', self.channel.id),
        ])
        self.channel._gc_chat_history(keep=10000)
        after = Message.search_count([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', self.channel.id),
        ])
        self.assertEqual(before, after, "GC should not prune below keep threshold")

    def test_07_gc_prunes_excess_messages(self):
        """GC removes old messages, keeping only the N most recent."""
        if not self.channel:
            self.skipTest("#english channel not found")
        Message = self.env['mail.message'].sudo()
        self._post_messages(15)
        self.channel._gc_chat_history(keep=5)
        remaining = Message.search_count([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', self.channel.id),
        ])
        self.assertLessEqual(remaining, 5,
                             "GC should keep at most 5 messages when keep=5")


class TestAddFromChat(TransactionCase):
    """Verify add_from_chat controller logic via model calls."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env.ref('base.user_demo', raise_if_not_found=False)
        if not cls.user:
            cls.user = cls.env['res.users'].sudo().create({
                'name': 'Chat Test User',
                'login': 'chat_test_user@lexora.test',
                'groups_id': [(4, cls.env.ref('language_security.group_language_user').id)],
            })
        cls.Entry = cls.env['language.entry'].sudo()

    def _make_entry(self, text, lang='en'):
        return self.Entry.create({
            'source_text': text,
            'source_language': lang,
            'owner_id': self.user.id,
            'type': 'word' if len(text.split()) == 1 else 'phrase',
            'created_from': 'copied_from_chat',
        })

    def test_08_create_entry_from_chat_word(self):
        entry = self._make_entry('helicopter')
        self.assertEqual(entry.created_from, 'copied_from_chat')
        self.assertEqual(entry.source_language, 'en')

    def test_09_create_entry_from_chat_phrase(self):
        entry = self._make_entry('black hole sun', 'en')
        self.assertEqual(entry.type, 'phrase')

    def test_10_duplicate_chat_entry_raises(self):
        self._make_entry('cosmos42')
        with self.assertRaises(ValidationError):
            self._make_entry('cosmos42')

    def test_11_chat_entry_provenance_field(self):
        entry = self._make_entry('quasar')
        self.assertEqual(entry.created_from, 'copied_from_chat')

    def test_12_chat_entry_owner_is_set(self):
        entry = self._make_entry('nebula')
        self.assertEqual(entry.owner_id.id, self.user.id)
