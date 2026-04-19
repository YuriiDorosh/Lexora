"""Tests for vocabulary search, filter, and sort logic (M8 UI refinement).

Tests exercise the ORM-level building blocks used by the vocabulary_list
controller: search by source_text, search through translation text, SRS
state filtering, and difficulty-sort ordering.  No HTTP is involved.
"""

from odoo.tests.common import TransactionCase


class TestVocabularySearch(TransactionCase):
    """Verify domain-building and ORM queries used by the Pro Dashboard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a dedicated portal user (gets Language User via implied_ids)
        cls.user = cls.env['res.users'].sudo().create({
            'name': 'VocabSearch TestUser',
            'login': 'vocabsearch@lexora.test',
            'email': 'vocabsearch@lexora.test',
            'groups_id': [(4, cls.env.ref('base.group_portal').id)],
        })

        Entry = cls.env['language.entry'].sudo()
        # Create test entries
        cls.e_apple = Entry.create({
            'source_text': 'apple',
            'source_language': 'en',
            'type': 'word',
            'owner_id': cls.user.id,
        })
        cls.e_banana = Entry.create({
            'source_text': 'banana',
            'source_language': 'en',
            'type': 'word',
            'owner_id': cls.user.id,
        })
        cls.e_cherry = Entry.create({
            'source_text': 'cherry',
            'source_language': 'en',
            'type': 'word',
            'owner_id': cls.user.id,
        })
        cls.e_ua = Entry.create({
            'source_text': 'яблуко',
            'source_language': 'uk',
            'type': 'word',
            'owner_id': cls.user.id,
        })

        # Ensure e_ua has an en translation containing 'apple' for cross-lang search.
        # Use write-or-create because the entry's create() override may have already
        # enqueued a stub translation if the user has learning languages set.
        Tr = cls.env['language.translation'].sudo()
        existing_tr = Tr.search([
            ('entry_id', '=', cls.e_ua.id),
            ('target_language', '=', 'en'),
        ], limit=1)
        if existing_tr:
            existing_tr.write({'translated_text': 'apple', 'status': 'completed'})
        else:
            Tr.create({
                'entry_id': cls.e_ua.id,
                'target_language': 'en',
                'translated_text': 'apple',
                'status': 'completed',
            })

        # Create SRS review cards for apple (new) and banana (learning)
        Review = cls.env['language.review'].sudo()
        cls.card_apple = Review.create({
            'entry_id': cls.e_apple.id,
            'user_id': cls.user.id,
            'state': 'new',
        })
        cls.card_banana = Review.create({
            'entry_id': cls.e_banana.id,
            'user_id': cls.user.id,
            'state': 'learning',
            'ease_factor': 1.5,  # hard word
        })
        # cherry has no review card → unstarted

    # ── Helpers ──────────────────────────────────────────────────────── #

    def _search_entries(self, search='', filterby='all'):
        """Replicate the domain logic from vocabulary_list controller."""
        uid = self.user.id
        domain = [('owner_id', '=', uid)]

        if search:
            trans_ids = self.env['language.translation'].sudo().search([
                ('translated_text', 'ilike', search),
                ('entry_id.owner_id', '=', uid),
            ]).mapped('entry_id').ids
            domain += ['|', ('source_text', 'ilike', search), ('id', 'in', trans_ids)]

        if filterby in ('new', 'learning', 'review'):
            srs_ids = self.env['language.review'].sudo().search([
                ('user_id', '=', uid),
                ('state', '=', filterby),
            ]).mapped('entry_id').ids
            domain += [('id', 'in', srs_ids)]
        elif filterby == 'unstarted':
            started = self.env['language.review'].sudo().search(
                [('user_id', '=', uid)]
            ).mapped('entry_id').ids
            domain += [('id', 'not in', started)]

        return self.env['language.entry'].sudo().search(domain)

    def _difficulty_order(self):
        """Replicate difficulty sort: reviewed entries by EF asc, then unreviewed."""
        uid = self.user.id
        domain = [('owner_id', '=', uid)]
        all_entries = self.env['language.entry'].sudo().search(domain)
        all_id_set  = set(all_entries.ids)
        reviews     = self.env['language.review'].sudo().search(
            [('user_id', '=', uid), ('entry_id', 'in', list(all_id_set))],
            order='ease_factor asc, id asc',
        )
        reviewed_ids   = [r.entry_id.id for r in reviews if r.entry_id.id in all_id_set]
        unreviewed_ids = [eid for eid in all_entries.ids if eid not in set(reviewed_ids)]
        return reviewed_ids + unreviewed_ids

    # ── Search tests ─────────────────────────────────────────────────── #

    def test_01_search_by_source_text(self):
        results = self._search_entries(search='apple')
        self.assertIn(self.e_apple, results)
        self.assertNotIn(self.e_banana, results)

    def test_02_search_is_case_insensitive(self):
        results = self._search_entries(search='APPLE')
        self.assertIn(self.e_apple, results)

    def test_03_search_partial_match(self):
        results = self._search_entries(search='anan')
        self.assertIn(self.e_banana, results)
        self.assertNotIn(self.e_apple, results)

    def test_04_search_finds_entry_via_translation_text(self):
        # e_ua has translated_text='apple' → search 'apple' should find it
        results = self._search_entries(search='apple')
        self.assertIn(self.e_ua, results, 'Cross-lang search via translation should match e_ua')

    def test_05_search_empty_returns_all_user_entries(self):
        results = self._search_entries(search='')
        self.assertIn(self.e_apple, results)
        self.assertIn(self.e_banana, results)
        self.assertIn(self.e_cherry, results)
        self.assertIn(self.e_ua, results)

    def test_06_search_no_match_returns_empty(self):
        results = self._search_entries(search='xyzzy_nonexistent_word')
        self.assertFalse(results)

    def test_07_search_does_not_cross_user_boundary(self):
        # Create an entry for a different user with source_text='apple'
        other_user = self.env['res.users'].sudo().create({
            'name': 'Other User',
            'login': 'other_vocab@lexora.test',
            'email': 'other_vocab@lexora.test',
            'groups_id': [(4, self.env.ref('base.group_portal').id)],
        })
        self.env['language.entry'].sudo().create({
            'source_text': 'apple',
            'source_language': 'en',
            'type': 'word',
            'owner_id': other_user.id,
        })
        results = self._search_entries(search='apple')
        for entry in results:
            self.assertEqual(entry.owner_id.id, self.user.id, 'Must not return other users\' entries')

    # ── SRS state filter tests ────────────────────────────────────────── #

    def test_08_filter_new_returns_only_new_cards(self):
        results = self._search_entries(filterby='new')
        self.assertIn(self.e_apple, results)
        self.assertNotIn(self.e_banana, results)
        self.assertNotIn(self.e_cherry, results)

    def test_09_filter_learning_returns_only_learning_cards(self):
        results = self._search_entries(filterby='learning')
        self.assertIn(self.e_banana, results)
        self.assertNotIn(self.e_apple, results)
        self.assertNotIn(self.e_cherry, results)

    def test_10_filter_review_returns_empty_when_no_review_cards(self):
        results = self._search_entries(filterby='review')
        # None of our test entries have state='review'
        for entry in results:
            self.assertIn(entry.id, [self.e_apple.id, self.e_banana.id,
                                      self.e_cherry.id, self.e_ua.id])
        # More precisely: apple=new, banana=learning → no review state entries
        self.assertNotIn(self.e_apple, results)
        self.assertNotIn(self.e_banana, results)

    def test_11_filter_unstarted_returns_entries_with_no_card(self):
        results = self._search_entries(filterby='unstarted')
        # cherry and e_ua have no review card
        self.assertIn(self.e_cherry, results)
        self.assertIn(self.e_ua, results)
        # apple and banana have cards
        self.assertNotIn(self.e_apple, results)
        self.assertNotIn(self.e_banana, results)

    def test_12_filter_all_returns_all_entries(self):
        results = self._search_entries(filterby='all')
        ids = results.ids
        self.assertIn(self.e_apple.id, ids)
        self.assertIn(self.e_banana.id, ids)
        self.assertIn(self.e_cherry.id, ids)
        self.assertIn(self.e_ua.id, ids)

    # ── Combined search + filter ────────────────────────────────────── #

    def test_13_search_and_filter_combined(self):
        # Search 'apple' AND filter 'new' → only e_apple (e_ua is 'unstarted')
        results = self._search_entries(search='apple', filterby='new')
        self.assertIn(self.e_apple, results)
        self.assertNotIn(self.e_ua, results)

    def test_14_search_and_filter_no_match(self):
        results = self._search_entries(search='banana', filterby='new')
        # banana has state=learning, not new → empty
        self.assertFalse(results)

    # ── Difficulty sort ───────────────────────────────────────────────── #

    def test_15_difficulty_sort_lowest_ef_first(self):
        ordered_ids = self._difficulty_order()
        # banana has ef=1.5 (set above), apple has ef=2.5 (default)
        # → banana should come before apple
        banana_pos = ordered_ids.index(self.e_banana.id)
        apple_pos  = ordered_ids.index(self.e_apple.id)
        self.assertLess(banana_pos, apple_pos,
                        'Harder words (lower EF) must come before easier ones')

    def test_16_difficulty_sort_unreviewed_go_last(self):
        ordered_ids = self._difficulty_order()
        cherry_pos = ordered_ids.index(self.e_cherry.id)
        ua_pos     = ordered_ids.index(self.e_ua.id)
        # Reviewed entries (apple, banana) come before unreviewed (cherry, ua)
        reviewed_positions = [ordered_ids.index(self.e_apple.id),
                               ordered_ids.index(self.e_banana.id)]
        max_reviewed_pos = max(reviewed_positions)
        self.assertGreater(cherry_pos, max_reviewed_pos)
        self.assertGreater(ua_pos,     max_reviewed_pos)
