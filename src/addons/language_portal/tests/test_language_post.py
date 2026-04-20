"""Tests for M7 Posts — model, state machine, comments, copy-to-list provenance."""

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError


def _make_user(env, name, groups=()):
    user = env['res.users'].sudo().create({
        'name': name,
        'login': f'{name.lower().replace(" ", "_")}@lexora.test',
        'groups_id': [(4, env.ref(g).id) for g in groups],
    })
    return user


class TestLanguagePost(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = _make_user(cls.env, 'Post Author',
                                ['language_security.group_language_user'])
        cls.moderator = _make_user(cls.env, 'Post Moderator',
                                   ['language_security.group_language_moderator'])
        cls.reader = _make_user(cls.env, 'Post Reader',
                                ['language_security.group_language_user'])
        cls.Post = cls.env['language.post'].sudo()

    def _draft(self, title='Test Post', author=None):
        return self.Post.create({
            'title': title,
            'body': '<p>Hello world</p>',
            'language': 'en',
            'status': 'draft',
            'author_id': (author or self.author).id,
        })

    # --- Basic creation ---

    def test_01_create_draft(self):
        post = self._draft()
        self.assertEqual(post.status, 'draft')
        self.assertTrue(post.slug)

    def test_02_slug_computed_from_title(self):
        post = self._draft('Hello World Article')
        self.assertIn('hello', post.slug)
        self.assertIn('world', post.slug)

    def test_03_summary_strips_html(self):
        post = self._draft()
        self.assertNotIn('<p>', post.summary)
        self.assertIn('Hello', post.summary)

    # --- State machine ---

    def test_04_submit_draft(self):
        post = self._draft()
        post.action_submit()
        self.assertEqual(post.status, 'pending')

    def test_05_cannot_submit_non_draft(self):
        post = self._draft()
        post.action_submit()
        with self.assertRaises(UserError):
            post.action_submit()

    def test_06_approve_sets_published(self):
        post = self._draft()
        post.action_submit()
        post.with_user(self.moderator).action_approve()
        self.assertEqual(post.status, 'published')
        self.assertTrue(post.published_date)

    def test_07_reject_sets_rejected(self):
        post = self._draft()
        post.action_submit()
        post.with_user(self.moderator).action_reject()
        self.assertEqual(post.status, 'rejected')

    def test_08_retract_pending_to_draft(self):
        post = self._draft()
        post.action_submit()
        post.with_user(self.author).action_retract()
        self.assertEqual(post.status, 'draft')

    def test_09_retract_rejected_to_draft(self):
        post = self._draft()
        post.action_submit()
        post.with_user(self.moderator).action_reject()
        post.with_user(self.author).action_retract()
        self.assertEqual(post.status, 'draft')

    def test_10_non_moderator_cannot_approve(self):
        post = self._draft()
        post.action_submit()
        with self.assertRaises(AccessError):
            post.with_user(self.author).action_approve()

    def test_11_non_moderator_cannot_reject(self):
        post = self._draft()
        post.action_submit()
        with self.assertRaises(AccessError):
            post.with_user(self.author).action_reject()

    def test_12_wrong_author_cannot_retract(self):
        post = self._draft()
        post.action_submit()
        with self.assertRaises(AccessError):
            post.with_user(self.reader).action_retract()


class TestPostComment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = _make_user(cls.env, 'Comment Author',
                                ['language_security.group_language_user'])
        cls.Post = cls.env['language.post'].sudo()
        cls.Comment = cls.env['language.post.comment'].sudo()
        cls.post = cls.Post.create({
            'title': 'Comment Test Post',
            'body': '<p>body</p>',
            'language': 'en',
            'status': 'published',
            'author_id': cls.author.id,
        })

    def test_13_add_comment(self):
        comment = self.Comment.create({
            'post_id': self.post.id,
            'author_id': self.author.id,
            'body': 'Nice article!',
        })
        self.assertEqual(comment.post_id.id, self.post.id)

    def test_14_comment_count_on_post(self):
        before = self.post.comment_count
        self.Comment.create({
            'post_id': self.post.id,
            'author_id': self.author.id,
            'body': 'Another comment',
        })
        self.post.invalidate_recordset()
        self.assertEqual(self.post.comment_count, before + 1)

    def test_15_mention_parses_at_login(self):
        user = _make_user(self.env, 'Mentioned User',
                          ['language_security.group_language_user'])
        comment = self.Comment.create({
            'post_id': self.post.id,
            'author_id': self.author.id,
            'body': f'Hey @{user.login.split("@")[0]}!',
        })
        self.assertIn(user, comment.mention_ids)

    def test_16_comment_delete(self):
        comment = self.Comment.create({
            'post_id': self.post.id,
            'author_id': self.author.id,
            'body': 'To delete',
        })
        comment_id = comment.id
        comment.unlink()
        self.assertFalse(self.Comment.browse(comment_id).exists())


class TestCopyFromPost(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = _make_user(cls.env, 'Copy User',
                              ['language_security.group_language_user'])
        cls.post = cls.env['language.post'].sudo().create({
            'title': 'Copy Source Post',
            'body': '<p>apple яблуко</p>',
            'language': 'en',
            'status': 'published',
            'author_id': cls.user.id,
        })
        cls.Entry = cls.env['language.entry'].sudo()

    def test_17_copy_sets_provenance(self):
        entry = self.Entry.create({
            'source_text': 'cosmos',
            'source_language': 'en',
            'owner_id': self.user.id,
            'type': 'word',
            'created_from': 'copied_from_post',
            'copied_from_post_id': self.post.id,
        })
        self.assertEqual(entry.created_from, 'copied_from_post')
        self.assertEqual(entry.copied_from_post_id.id, self.post.id)

    def test_18_copy_duplicate_raises(self):
        self.Entry.create({
            'source_text': 'stargazer',
            'source_language': 'en',
            'owner_id': self.user.id,
            'type': 'word',
            'created_from': 'copied_from_post',
            'copied_from_post_id': self.post.id,
        })
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.Entry.create({
                'source_text': 'stargazer',
                'source_language': 'en',
                'owner_id': self.user.id,
                'type': 'word',
                'created_from': 'copied_from_post',
                'copied_from_post_id': self.post.id,
            })
