from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLanguageEntry(TransactionCase):
    """Tests for language.entry model: creation, dedup, sharing, copy."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create two regular users for multi-user tests
        cls.user_a = cls.env['res.users'].create({
            'name': 'Test User A',
            'login': 'test_entry_user_a@lexora.test',
            'email': 'test_entry_user_a@lexora.test',
            'groups_id': [(6, 0, [cls.env.ref('language_security.group_language_user').id])],
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'Test User B',
            'login': 'test_entry_user_b@lexora.test',
            'email': 'test_entry_user_b@lexora.test',
            'groups_id': [(6, 0, [cls.env.ref('language_security.group_language_user').id])],
        })
        cls.Entry = cls.env['language.entry'].sudo()

    def test_create_basic_entry(self):
        entry = self.Entry.create({
            'source_text': 'apple',
            'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        self.assertEqual(entry.source_text, 'apple')
        self.assertEqual(entry.normalized_text, 'apple')
        self.assertEqual(entry.type, 'word')
        self.assertEqual(entry.status, 'active')
        self.assertFalse(entry.is_shared)

    def test_normalized_text_stored_on_create(self):
        """normalized_text is computed and stored at create time."""
        entry = self.Entry.create({
            'source_text': '  Apple  ',
            'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        self.assertEqual(entry.normalized_text, 'apple')

    def test_dedup_exact_duplicate_blocked(self):
        """Creating an exact duplicate raises ValidationError."""
        self.Entry.create({
            'source_text': 'apple',
            'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        with self.assertRaises(ValidationError):
            self.Entry.create({
                'source_text': 'apple',
                'source_language': 'en',
                'owner_id': self.user_a.id,
            })

    def test_dedup_case_insensitive(self):
        """'Apple ' and 'apple' are duplicates (normalize lowercases + strips)."""
        self.Entry.create({
            'source_text': 'apple',
            'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        with self.assertRaises(ValidationError):
            self.Entry.create({
                'source_text': 'Apple ',
                'source_language': 'en',
                'owner_id': self.user_a.id,
            })

    def test_dedup_trailing_punctuation(self):
        """'How are you?' and 'How are you' are duplicates."""
        self.Entry.create({
            'source_text': 'How are you?',
            'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        with self.assertRaises(ValidationError):
            self.Entry.create({
                'source_text': 'How are you',
                'source_language': 'en',
                'owner_id': self.user_a.id,
            })

    def test_dedup_different_language_allowed(self):
        """Same text in different languages is NOT a duplicate."""
        self.Entry.create({
            'source_text': 'apple',
            'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        # Same text but different language — must not raise
        entry2 = self.Entry.create({
            'source_text': 'apple',
            'source_language': 'uk',
            'owner_id': self.user_a.id,
        })
        self.assertTrue(entry2.id)

    def test_dedup_different_owner_allowed(self):
        """Same text+language but different owner is NOT a duplicate."""
        self.Entry.create({
            'source_text': 'apple',
            'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        entry2 = self.Entry.create({
            'source_text': 'apple',
            'source_language': 'en',
            'owner_id': self.user_b.id,
        })
        self.assertTrue(entry2.id)

    def test_dedup_type_not_in_key(self):
        """Type is NOT part of the dedup key (ADR-003).
        Same text + language + owner with different type → duplicate."""
        self.Entry.create({
            'source_text': 'run fast',
            'source_language': 'en',
            'type': 'phrase',
            'owner_id': self.user_a.id,
        })
        with self.assertRaises(ValidationError):
            self.Entry.create({
                'source_text': 'run fast',
                'source_language': 'en',
                'type': 'collocation',   # different type, same key
                'owner_id': self.user_a.id,
            })

    def test_sharing_toggle(self):
        """is_shared defaults to False; can be toggled to True."""
        entry = self.Entry.create({
            'source_text': 'tree',
            'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        self.assertFalse(entry.is_shared)
        entry.is_shared = True
        self.assertTrue(entry.is_shared)

    def test_shared_entry_visible_to_other_user(self):
        """A shared entry is returned by search() for another Language User (record rule)."""
        entry = self.Entry.create({
            'source_text': 'forest',
            'source_language': 'en',
            'owner_id': self.user_a.id,
            'is_shared': True,
        })
        found = self.env['language.entry'].with_user(self.user_b).search([('id', '=', entry.id)])
        self.assertTrue(found)
        self.assertEqual(found.source_text, 'forest')

    def test_private_entry_not_visible_to_other_user(self):
        """A private entry is NOT returned by search() for another user (record rule).

        Note: browse() + exists() in Odoo does NOT apply record rules;
        only search() respects them.  We use search() here deliberately.
        """
        entry = self.Entry.create({
            'source_text': 'secret_word_xyz',
            'source_language': 'en',
            'owner_id': self.user_a.id,
            'is_shared': False,
        })
        found = self.env['language.entry'].with_user(self.user_b).search([('id', '=', entry.id)])
        self.assertFalse(found)

    def test_copy_to_user(self):
        """copy_to_user creates a new entry with correct provenance fields."""
        original = self.Entry.create({
            'source_text': 'sky',
            'source_language': 'en',
            'owner_id': self.user_a.id,
            'is_shared': True,
        })
        copied = original.copy_to_user(self.user_b.id)
        self.assertEqual(copied.source_text, 'sky')
        self.assertEqual(copied.owner_id.id, self.user_b.id)
        self.assertEqual(copied.created_from, 'copied_from_entry')
        self.assertEqual(copied.copied_from_user_id.id, self.user_a.id)
        self.assertEqual(copied.copied_from_entry_id.id, original.id)

    def test_copy_to_user_duplicate_blocked(self):
        """Copying an entry the target user already has raises ValidationError."""
        self.Entry.create({
            'source_text': 'sky',
            'source_language': 'en',
            'owner_id': self.user_b.id,
        })
        original = self.Entry.create({
            'source_text': 'sky',
            'source_language': 'en',
            'owner_id': self.user_a.id,
            'is_shared': True,
        })
        with self.assertRaises(ValidationError):
            original.copy_to_user(self.user_b.id)
