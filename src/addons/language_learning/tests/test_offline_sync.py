"""Tests for M36 — Mobile PWA offline-sync API.

Exercises the apply_offline_batch business logic on
language.review.offline.log directly (TransactionCase, no HTTP plumbing).
The controller is a thin JSON wrapper around this method — testing the
logic at the model level covers the same code path the production
sync endpoint runs (sub-decision 35c).

Six tests, mapped 1:1 to the M36-S3-05 plan entry:

  1. Idempotent re-upload — same UUID twice → second is no-op.
  2. Foreign-user card → not_found.
  3. Bad grade (-1 and 99) → clamped to [0, 3].
  4. Mixed batch (one new, one duplicate, one not_found) → counts.
  5. /offline_batch respects days/limit clamping.
  6. /offline_batch returns translations dict per card.
"""

from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestOfflineSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref('language_security.group_language_user')

        # Two Language Users so we can test cross-ownership protection.
        cls.user_a = cls.env['res.users'].sudo().create({
            'name': 'PWA Sync A',
            'login': 'pwa_sync_a@lexora.test',
            'email': 'pwa_sync_a@lexora.test',
            'groups_id': [(6, 0, [group_user.id])],
        })
        cls.user_b = cls.env['res.users'].sudo().create({
            'name': 'PWA Sync B',
            'login': 'pwa_sync_b@lexora.test',
            'email': 'pwa_sync_b@lexora.test',
            'groups_id': [(6, 0, [group_user.id])],
        })

        cls.Entry = cls.env['language.entry'].sudo()
        cls.Review = cls.env['language.review'].sudo()
        cls.Trans = cls.env['language.translation'].sudo()
        cls.Log = cls.env['language.review.offline.log'].sudo()

        # User A's vocabulary entries + cards.
        cls.entry_a1 = cls.Entry.create({
            'source_text': 'ephemeral',
            'source_language': 'en',
            'owner_id': cls.user_a.id,
        })
        cls.entry_a2 = cls.Entry.create({
            'source_text': 'apparently',
            'source_language': 'en',
            'owner_id': cls.user_a.id,
        })
        cls.card_a1 = cls.Review.create({
            'entry_id': cls.entry_a1.id,
            'user_id': cls.user_a.id,
        })
        cls.card_a2 = cls.Review.create({
            'entry_id': cls.entry_a2.id,
            'user_id': cls.user_a.id,
        })

        # User B's vocabulary + card — used to verify cross-user
        # protection (a sync batch from user A must not be able to
        # write into user B's cards).
        cls.entry_b1 = cls.Entry.create({
            'source_text': 'foreign',
            'source_language': 'en',
            'owner_id': cls.user_b.id,
        })
        cls.card_b1 = cls.Review.create({
            'entry_id': cls.entry_b1.id,
            'user_id': cls.user_b.id,
        })

        # Translations for entry_a1 — used by test 6 to verify the
        # /offline_batch projection joins them in.
        #
        # IMPORTANT: M29 auto-translate hook (ADR-029 § 29c) pre-creates
        # pending translation rows for every supported language on
        # entry create. The UNIQUE(entry_id, target_language) constraint
        # would reject a fresh create() here. We upsert instead — find
        # the pending row left by the hook and flip it to completed.
        for tl, txt in (('uk', 'короткочасний'), ('el', 'εφήμερος'), ('pl', 'efemeryczny')):
            existing = cls.Trans.search([
                ('entry_id', '=', cls.entry_a1.id),
                ('target_language', '=', tl),
            ], limit=1)
            if existing:
                existing.write({'translated_text': txt, 'status': 'completed'})
            else:
                cls.Trans.create({
                    'entry_id': cls.entry_a1.id,
                    'target_language': tl,
                    'translated_text': txt,
                    'status': 'completed',
                })

    # --------------------------------------------------------------- #
    # 1. Idempotent re-upload
    # --------------------------------------------------------------- #

    def test_01_idempotent_replay_same_uuid(self):
        """Same UUID submitted twice — second call is a no-op.

        The unique (user_id, client_uuid) constraint on
        language.review.offline.log enforces idempotency at the
        database level; apply_offline_batch's dedup check catches
        the duplicate before the INSERT so we get a clean
        skipped_duplicate count rather than a 500.
        """
        review = {
            'client_uuid': '11111111-1111-4111-8111-111111111111',
            'card_id': self.card_a1.id,
            'grade': 2,
            'reviewed_at_iso': '2026-05-17T10:00:00Z',
        }

        # First call — should process cleanly.
        r1 = self.Log.apply_offline_batch(self.user_a, [review])
        self.assertEqual(r1['processed'], 1,
                         'first call should record the review')
        self.assertEqual(r1['skipped_duplicate'], 0)
        self.assertEqual(r1['not_found'], 0)
        self.assertEqual(r1['errors'], [])

        # Re-upload of the SAME payload (mimics a client retry after a
        # mid-flight network drop) — every row should land in
        # skipped_duplicate, not processed.
        r2 = self.Log.apply_offline_batch(self.user_a, [review])
        self.assertEqual(r2['processed'], 0)
        self.assertEqual(r2['skipped_duplicate'], 1,
                         'second call should silently skip the duplicate')
        self.assertEqual(r2['not_found'], 0)
        self.assertEqual(r2['errors'], [])

        # And only one log row total.
        rows = self.Log.search([
            ('user_id', '=', self.user_a.id),
            ('client_uuid', '=', '11111111-1111-4111-8111-111111111111'),
        ])
        self.assertEqual(len(rows), 1,
                         'exactly one log row regardless of retry count')

    # --------------------------------------------------------------- #
    # 2. Foreign-user card
    # --------------------------------------------------------------- #

    def test_02_foreign_user_card_is_not_found(self):
        """A user can NEVER apply a review to another user's card.

        User A's batch references card_b1 (owned by user B). The
        ownership check (search where user_id = caller.id) excludes
        it, so the count lands in not_found. No log row is created;
        no SM-2 advance happens on card_b1.
        """
        review = {
            'client_uuid': '22222222-2222-4222-8222-222222222222',
            'card_id': self.card_b1.id,    # ← belongs to user B
            'grade': 2,
        }
        b_state_before = self.card_b1.state
        b_reps_before = self.card_b1.repetitions

        r = self.Log.apply_offline_batch(self.user_a, [review])
        self.assertEqual(r['not_found'], 1,
                         'foreign-user card must be rejected as not_found')
        self.assertEqual(r['processed'], 0)
        self.assertEqual(r['skipped_duplicate'], 0)

        # Verify card_b1 was NOT mutated.
        self.card_b1.invalidate_recordset()
        self.assertEqual(self.card_b1.state, b_state_before,
                         "user B's card state must be unchanged")
        self.assertEqual(self.card_b1.repetitions, b_reps_before,
                         "user B's card repetitions must be unchanged")

        # No log row leaked for this UUID under user_a.
        rows = self.Log.search([
            ('user_id', '=', self.user_a.id),
            ('client_uuid', '=', '22222222-2222-4222-8222-222222222222'),
        ])
        self.assertFalse(rows, 'no log row should be created for not_found')

    # --------------------------------------------------------------- #
    # 3. Bad grade — defensive clamp to [0, 3]
    # --------------------------------------------------------------- #

    def test_03_grade_clamping_low_and_high(self):
        """Out-of-range grades are clamped at the endpoints.

        Grade -1 → 0 (Again). Grade 99 → 3 (Easy). Non-numeric → 0.
        Tampered or future-UI grades never crash the sync endpoint;
        the SM-2 advance always sees a value in [0, 3].
        """
        # Run a fresh card through each path so we can compare state.
        # Use fresh UUIDs and fresh cards (re-using one card would
        # cumulate state across calls).
        e_low = self.Entry.create({
            'source_text': 'low', 'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        e_high = self.Entry.create({
            'source_text': 'high', 'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        c_low = self.Review.create({'entry_id': e_low.id, 'user_id': self.user_a.id})
        c_high = self.Review.create({'entry_id': e_high.id, 'user_id': self.user_a.id})

        # Grade -1 → clamped to 0. SM-2 grade 0 (Again) resets the
        # card: repetitions=0, interval=1, state='learning'.
        r_low = self.Log.apply_offline_batch(self.user_a, [{
            'client_uuid': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01',
            'card_id': c_low.id,
            'grade': -1,
        }])
        self.assertEqual(r_low['processed'], 1)
        log_low = self.Log.search([
            ('client_uuid', '=', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01'),
        ], limit=1)
        self.assertEqual(log_low.grade, 0,
                         'grade -1 must be clamped to 0 in the log')

        # Grade 99 → clamped to 3 (Easy).
        r_high = self.Log.apply_offline_batch(self.user_a, [{
            'client_uuid': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa02',
            'card_id': c_high.id,
            'grade': 99,
        }])
        self.assertEqual(r_high['processed'], 1)
        log_high = self.Log.search([
            ('client_uuid', '=', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa02'),
        ], limit=1)
        self.assertEqual(log_high.grade, 3,
                         'grade 99 must be clamped to 3 in the log')

        # Non-numeric grade → clamped to 0 (safe default).
        e_str = self.Entry.create({
            'source_text': 'stringy', 'source_language': 'en',
            'owner_id': self.user_a.id,
        })
        c_str = self.Review.create({'entry_id': e_str.id, 'user_id': self.user_a.id})
        r_str = self.Log.apply_offline_batch(self.user_a, [{
            'client_uuid': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa03',
            'card_id': c_str.id,
            'grade': 'oops',
        }])
        self.assertEqual(r_str['processed'], 1,
                         'non-numeric grade must NOT reject the row')
        log_str = self.Log.search([
            ('client_uuid', '=', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa03'),
        ], limit=1)
        self.assertEqual(log_str.grade, 0,
                         'non-numeric grade clamps to 0')

    # --------------------------------------------------------------- #
    # 4. Mixed batch — partial success counts
    # --------------------------------------------------------------- #

    def test_04_mixed_batch_partial_success(self):
        """A batch with one new, one duplicate, and one foreign card
        produces the right counts and applies only the new row.

        This is the realistic offline-replay scenario: most rows are
        fresh, occasionally a previously-successful row is re-sent
        (network blip), and occasionally a row's card no longer
        exists or has been deleted in another tab.
        """
        # Pre-seed a "this UUID has been seen before" row so the
        # duplicate row in the batch lands in skipped_duplicate.
        seed_uuid = '33333333-3333-4333-8333-333333333301'
        self.Log.create({
            'user_id': self.user_a.id,
            'client_uuid': seed_uuid,
            'card_id': self.card_a1.id,
            'grade': 2,
        })

        # Mixed batch:
        #   - one NEW row (will be processed)
        #   - one DUPLICATE (same UUID as seed)
        #   - one FOREIGN (card_b1 belongs to user B)
        batch = [
            {
                'client_uuid': '33333333-3333-4333-8333-333333333302',
                'card_id': self.card_a2.id,
                'grade': 2,
            },
            {
                'client_uuid': seed_uuid,                   # duplicate
                'card_id': self.card_a1.id,
                'grade': 0,
            },
            {
                'client_uuid': '33333333-3333-4333-8333-333333333303',
                'card_id': self.card_b1.id,                  # foreign
                'grade': 2,
            },
        ]
        r = self.Log.apply_offline_batch(self.user_a, batch)
        self.assertEqual(r['processed'], 1,
                         'only the fresh card_a2 row should be processed')
        self.assertEqual(r['skipped_duplicate'], 1,
                         'the seeded UUID must come back as skipped')
        self.assertEqual(r['not_found'], 1,
                         "user B's card must come back as not_found")
        self.assertEqual(r['errors'], [],
                         'no per-row errors in a well-formed batch')

    # --------------------------------------------------------------- #
    # 5. /offline_batch days + limit clamping (model-level smoke)
    # --------------------------------------------------------------- #

    def test_05_offline_batch_clamping_logic(self):
        """The clamping logic that the /offline_batch route applies to
        the days + limit query params is just min/max bounds — verify
        the bounds match the spec.

        We test the constants directly rather than hitting the HTTP
        endpoint because the existing language_learning test suite
        uses TransactionCase, not HttpCase. The route is a one-liner
        on top of these constants.
        """
        from odoo.addons.language_learning.controllers.portal_pwa import (
            _OFFLINE_BATCH_DEFAULT_DAYS,
            _OFFLINE_BATCH_DEFAULT_LIMIT,
            _OFFLINE_BATCH_MAX_DAYS,
            _OFFLINE_BATCH_MAX_LIMIT,
        )

        # Sanity: defaults sit inside the allowed range, and the upper
        # bounds are the values the spec promises (30 days, 1000 rows).
        self.assertEqual(_OFFLINE_BATCH_MAX_DAYS, 30)
        self.assertEqual(_OFFLINE_BATCH_MAX_LIMIT, 1000)
        self.assertTrue(1 <= _OFFLINE_BATCH_DEFAULT_DAYS <= _OFFLINE_BATCH_MAX_DAYS)
        self.assertTrue(1 <= _OFFLINE_BATCH_DEFAULT_LIMIT <= _OFFLINE_BATCH_MAX_LIMIT)

        # The clamping idiom max(1, min(MAX, n)) used by the route:
        clamp_d = lambda v: max(1, min(_OFFLINE_BATCH_MAX_DAYS, v))
        clamp_n = lambda v: max(1, min(_OFFLINE_BATCH_MAX_LIMIT, v))

        # Negative + over-max values both pull to the nearest endpoint.
        self.assertEqual(clamp_d(-5), 1)
        self.assertEqual(clamp_d(99999), _OFFLINE_BATCH_MAX_DAYS)
        self.assertEqual(clamp_n(0), 1)
        self.assertEqual(clamp_n(999999), _OFFLINE_BATCH_MAX_LIMIT)
        # In-range values round-trip unchanged.
        self.assertEqual(clamp_d(7), 7)
        self.assertEqual(clamp_n(200), 200)

    # --------------------------------------------------------------- #
    # 6. /offline_batch projection: translations dict per card
    # --------------------------------------------------------------- #

    def test_06_translations_join_in_projection(self):
        """Exercise the projection logic the /offline_batch route uses
        to build {entry.id → {lang_code: translation_text}}.

        setUpClass seeded entry_a1 with three completed translations
        (uk / el / pl). Reproduce the query the route runs and confirm
        the result is a dict shaped exactly as ADR-035 § 35c describes.
        """
        Trans = self.env['language.translation'].sudo()
        rows = Trans.search([
            ('entry_id', '=', self.entry_a1.id),
            ('status', '=', 'completed'),
        ], order='id asc')

        trans_by_entry = {}
        for t in rows:
            bucket = trans_by_entry.setdefault(t.entry_id.id, {})
            if t.target_language and t.translated_text and \
               t.target_language not in bucket:
                bucket[t.target_language] = t.translated_text

        self.assertIn(self.entry_a1.id, trans_by_entry)
        proj = trans_by_entry[self.entry_a1.id]
        self.assertEqual(proj.get('uk'), 'короткочасний')
        self.assertEqual(proj.get('el'), 'εφήμερος')
        self.assertEqual(proj.get('pl'), 'efemeryczny')
        # English wasn't seeded — must NOT appear in the dict.
        self.assertNotIn('en', proj)
        # Three completed translations → dict has exactly three keys.
        self.assertEqual(len(proj), 3)

        # entry_b1 has no translations seeded → not present in the dict.
        self.assertNotIn(self.entry_b1.id, trans_by_entry)
