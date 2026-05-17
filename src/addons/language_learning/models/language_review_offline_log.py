"""M36 — Offline-sync idempotency log.

One row per (user_id, client_uuid) pair successfully processed by
POST /lexora_api/sync_offline. The UNIQUE constraint enforces
idempotent re-uploads — if the client retries a batch after a
mid-flight network drop, every UUID in the second request that's
already here is silently skipped (sub-decision 35c).

Why a dedicated model rather than a Text/JSON field on
language.review:

  - Cleanly indexable for the duplicate check (single B-tree
    lookup, not a JSON scan).
  - Survives card deletion without orphan-record cleanup (the
    Many2one uses ondelete='set null' so cards can be deleted
    freely while the dedupe history stays intact).
  - Supports future analytics queries like "how many of this
    user's reviews came in via offline sync this month."
  - Keeps the language.review schema small — we already pack a lot
    of SM-2 state into that model.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


# SM-2 accepts grades 0..3 (Again / Hard / Good / Easy). The mobile UI in
# ADR-035 § 35e ships only 0 and 2, but we clamp defensively here in case
# the buffer carries a value from a future UI version or a tampered
# client request. Anything outside the range collapses to the nearest
# endpoint — never reject the row, just route to the safe grade.
_GRADE_MIN = 0
_GRADE_MAX = 3


def _clamp_grade(raw):
    """Coerce any value to a safe int in [0, 3]. Non-numeric → 0."""
    try:
        g = int(raw)
    except (TypeError, ValueError):
        return _GRADE_MIN
    if g < _GRADE_MIN:
        return _GRADE_MIN
    if g > _GRADE_MAX:
        return _GRADE_MAX
    return g


class LanguageReviewOfflineLog(models.Model):
    _name = 'language.review.offline.log'
    _description = 'Offline-sync idempotency log for SRS reviews (M36)'
    _order = 'applied_at desc, id desc'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        index=True,
        ondelete='cascade',
        help='Owner whose offline batch contained this UUID. Cascades on user delete '
             'so we never have orphan log rows pointing at deleted accounts.',
    )

    client_uuid = fields.Char(
        string='Client UUID',
        required=True,
        index=True,
        help='Client-generated UUID (typically crypto.randomUUID() in the browser). '
             'Paired with user_id under a UNIQUE constraint so re-uploads of the '
             'same offline batch are safe.',
    )

    card_id = fields.Many2one(
        'language.review',
        string='Card',
        ondelete='set null',
        help='The SRS card this review applied to. Set NULL rather than cascade '
             'on card delete so the dedup history survives card cleanup.',
    )

    grade = fields.Integer(
        string='Grade',
        help='SM-2 grade as recorded by the client. Clamped to 0..3 by the sync '
             'endpoint before reaching language.review.action_register_review().',
    )

    reviewed_at = fields.Datetime(
        string='Reviewed at (client clock)',
        help="Client-reported timestamp of when the user graded the card. "
             "Stored verbatim — we don't trust client clocks for SRS logic, "
             "but it's useful for retrospective analytics.",
    )

    applied_at = fields.Datetime(
        string='Applied at (server clock)',
        default=fields.Datetime.now,
        required=True,
        help='Server-side timestamp of when the sync endpoint accepted this UUID.',
    )

    _sql_constraints = [
        (
            'uuid_unique_per_user',
            'UNIQUE(user_id, client_uuid)',
            'Offline review UUID already processed for this user. '
            'Re-uploads of the same batch are silently skipped by the sync endpoint.',
        ),
    ]

    # ------------------------------------------------------------------
    # apply_offline_batch — sync-endpoint business logic
    # ------------------------------------------------------------------
    @api.model
    def apply_offline_batch(self, user, reviews):
        """Apply a batch of offline reviews for ``user``.

        Per row in ``reviews``:
          1. Validate the shape (client_uuid + card_id present).
          2. Dedup check against ``language.review.offline.log`` —
             ``(user.id, client_uuid)`` already present → skipped_duplicate.
          3. Card lookup — must exist AND be owned by ``user`` → otherwise
             not_found (could be a deleted card or someone else's).
          4. Grade clamp to [0, 3].
          5. ``card.action_register_review(grade)`` — the existing SM-2
             advance, unchanged from the M7 flow.
          6. Insert a fresh ``language.review.offline.log`` row so future
             re-uploads of this UUID are no-ops.

        Returns:
            dict with int counts and a list of per-row errors:
                {
                  'processed':         <int>,
                  'skipped_duplicate': <int>,
                  'not_found':         <int>,
                  'errors':            [{'client_uuid', 'message'}, ...]
                }

        Caller MUST hold sudo privileges — both the controller and the
        tests call this via ``env['language.review.offline.log'].sudo()``.
        Record-rule access checks for the underlying ``language.review``
        write happen inside ``action_register_review`` after we've
        verified the card ownership ourselves.
        """
        out = {
            'processed': 0,
            'skipped_duplicate': 0,
            'not_found': 0,
            'errors': [],
        }
        if not isinstance(reviews, (list, tuple)):
            out['errors'].append({'client_uuid': None,
                                  'message': 'reviews must be a list'})
            return out
        if not user or not user.id:
            out['errors'].append({'client_uuid': None,
                                  'message': 'user is required'})
            return out

        Log = self.sudo()
        Review = self.env['language.review'].sudo()

        for raw in reviews:
            if not isinstance(raw, dict):
                out['errors'].append({'client_uuid': None,
                                      'message': 'review row is not an object'})
                continue
            client_uuid = (raw.get('client_uuid') or '').strip()
            card_id = raw.get('card_id')
            if not client_uuid or not card_id:
                out['errors'].append({
                    'client_uuid': client_uuid or None,
                    'message': 'client_uuid and card_id are required',
                })
                continue

            # ── 2. Dedup check ───────────────────────────────────────
            existing = Log.search([
                ('user_id', '=', user.id),
                ('client_uuid', '=', client_uuid),
            ], limit=1)
            if existing:
                out['skipped_duplicate'] += 1
                continue

            # ── 3. Card lookup + ownership ───────────────────────────
            card = Review.search([
                ('id', '=', int(card_id)),
                ('user_id', '=', user.id),
            ], limit=1)
            if not card:
                out['not_found'] += 1
                continue

            # ── 4. Grade clamp ───────────────────────────────────────
            grade = _clamp_grade(raw.get('grade'))

            # ── 5. SM-2 advance via the existing flow ────────────────
            try:
                card.action_register_review(grade)
            except Exception as exc:  # pragma: no cover — defensive
                _logger.exception('action_register_review failed for card %s', card_id)
                out['errors'].append({
                    'client_uuid': client_uuid,
                    'message': 'action_register_review failed: %s' % exc,
                })
                continue

            # ── 6. Log the UUID so re-uploads are idempotent ─────────
            # Convert client-supplied ISO string to Datetime tolerantly:
            # the field is informational so we accept whatever parses.
            reviewed_at = None
            raw_dt = raw.get('reviewed_at_iso')
            if raw_dt:
                try:
                    reviewed_at = fields.Datetime.to_datetime(raw_dt)
                except Exception:
                    reviewed_at = None

            Log.create({
                'user_id': user.id,
                'client_uuid': client_uuid,
                'card_id': card.id,
                'grade': grade,
                'reviewed_at': reviewed_at,
            })
            out['processed'] += 1

        return out
