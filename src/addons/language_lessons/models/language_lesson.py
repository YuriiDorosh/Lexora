from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.language_words.models.language_lang import LANGUAGE_SELECTION

from .lesson_parser import parse_lesson_text

SOURCE_TYPE_SELECTION = [
    ('manual_text', 'Manual Text'),
    ('preply_extension', 'Preply Extension'),
    ('json_upload', 'JSON Upload'),
]

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('parsed', 'Parsed'),
    ('analyzed', 'Analyzed'),
    ('published', 'Published'),
    ('error', 'Error'),
]


class LanguageLesson(models.Model):
    """One imported tutoring lesson.

    Phase 1 (M39): parse -> analyze novelty -> auto-create language.entry
    for brand-new vocab/phrases. Course generation into website_slides is
    Phase 2 (ADR-038); this model deliberately has no channel_id field
    yet so Phase 2 can add tutor-access without reshaping Phase 1 data.
    """

    _name = 'language.lesson'
    _description = 'Imported Tutoring Lesson'
    _order = 'lesson_date desc, id desc'

    name = fields.Char(string='Topic', required=True, default='New Lesson')
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Owner',
        required=True,
        default=lambda self: self.env.uid,
        index=True,
        ondelete='cascade',
    )
    lesson_date = fields.Date(
        string='Lesson Date',
        required=True,
        default=lambda self: fields.Date.context_today(self),
        index=True,
    )
    tutor_name = fields.Char(string='Tutor')
    language = fields.Selection(
        selection=LANGUAGE_SELECTION,
        string='Language',
        required=True,
        default='en',
        index=True,
    )
    source_type = fields.Selection(
        selection=SOURCE_TYPE_SELECTION,
        string='Source',
        default='manual_text',
        required=True,
    )
    raw_payload = fields.Text(string='Raw Lesson Text')
    item_ids = fields.One2many(
        comodel_name='language.lesson.item',
        inverse_name='lesson_id',
        string='Items',
    )
    state = fields.Selection(
        selection=STATE_SELECTION,
        string='Status',
        default='draft',
        required=True,
        index=True,
    )
    error_message = fields.Text(string='Error Message')

    new_count = fields.Integer(string='New', compute='_compute_counts', store=True)
    seen_count = fields.Integer(string='Seen', compute='_compute_counts', store=True)
    known_count = fields.Integer(string='Known', compute='_compute_counts', store=True)
    correction_count = fields.Integer(string='Corrections', compute='_compute_counts', store=True)

    @api.depends('item_ids.novelty', 'item_ids.item_type')
    def _compute_counts(self):
        for lesson in self:
            items = lesson.item_ids
            lesson.new_count = len(items.filtered(lambda i: i.novelty == 'new'))
            lesson.seen_count = len(items.filtered(lambda i: i.novelty == 'seen'))
            lesson.known_count = len(items.filtered(lambda i: i.novelty == 'known'))
            lesson.correction_count = len(items.filtered(lambda i: i.item_type == 'correction'))

    # ------------------------------------------------------------------
    # Parsing (ADR-038 § 38a — rule-based, no ORM inside the parser itself)
    # ------------------------------------------------------------------

    def action_parse(self):
        for lesson in self:
            try:
                parsed = parse_lesson_text(lesson.raw_payload)
            except Exception as exc:  # noqa: BLE001 — surface any parser bug as a visible job error
                lesson.write({'state': 'error', 'error_message': str(exc)})
                continue

            lesson.item_ids.unlink()

            vals = {}
            if not lesson.name or lesson.name == 'New Lesson':
                if parsed.get('topic'):
                    vals['name'] = parsed['topic']

            item_vals_list = [
                {
                    'lesson_id': lesson.id,
                    'sequence': (idx + 1) * 10,
                    'item_type': item['item_type'],
                    'text': item['text'],
                    'translation_hint': item['translation_hint'],
                    'corrected_text': item['corrected_text'],
                    'context': item['context'],
                }
                for idx, item in enumerate(parsed['items'])
            ]
            if item_vals_list:
                self.env['language.lesson.item'].create(item_vals_list)

            vals.update({'state': 'parsed', 'error_message': False})
            lesson.write(vals)
        return True

    def action_reparse(self):
        for lesson in self:
            lesson.item_ids.unlink()
            lesson.write({'state': 'draft', 'error_message': False})
        return self.action_parse()

    # ------------------------------------------------------------------
    # Novelty analysis (ADR-038 § 38b/38d)
    # ------------------------------------------------------------------

    def action_analyze_novelty(self):
        for lesson in self:
            if lesson.state not in ('parsed', 'analyzed'):
                raise UserError('Parse the lesson before analyzing novelty.')

            Entry = self.env['language.entry']
            Item = self.env['language.lesson.item']

            entries = Entry.search([
                ('owner_id', '=', lesson.user_id.id),
                ('source_language', '=', lesson.language),
                ('status', '=', 'active'),
            ])
            entry_by_norm = {e.normalized_text: e for e in entries}

            review_by_entry = {}
            if 'language.review' in self.env.registry:
                Review = self.env['language.review']
                reviews = Review.search([
                    ('user_id', '=', lesson.user_id.id),
                    ('entry_id', 'in', entries.ids),
                ])
                review_by_entry = {r.entry_id.id: r for r in reviews}

            prior_items = Item.search([
                ('lesson_id.user_id', '=', lesson.user_id.id),
                ('lesson_id.language', '=', lesson.language),
                ('lesson_id.lesson_date', '<', lesson.lesson_date),
                ('item_type', 'in', ('vocab', 'phrase')),
            ])
            prior_by_norm = {}
            for prior_item in prior_items:
                key = prior_item.text_normalized
                existing = prior_by_norm.get(key)
                if existing is None or prior_item.lesson_id.lesson_date < existing.lesson_id.lesson_date:
                    prior_by_norm[key] = prior_item

            prior_correction_norms = {
                it.text_normalized
                for it in Item.search([
                    ('lesson_id.user_id', '=', lesson.user_id.id),
                    ('lesson_id.language', '=', lesson.language),
                    ('lesson_id.lesson_date', '<', lesson.lesson_date),
                    ('item_type', '=', 'correction'),
                ])
            }

            weights = lesson._get_emphasis_weights()
            known_due_today = lesson._get_known_due_today()

            for item in lesson.item_ids:
                if item.item_type in ('vocab', 'phrase'):
                    lesson._classify_vocab_item(
                        item, entry_by_norm, review_by_entry, prior_by_norm, weights, known_due_today,
                    )
                elif item.item_type == 'correction':
                    is_recurring = item.text_normalized in prior_correction_norms
                    item.write({
                        'is_recurring_mistake': is_recurring,
                        'emphasis_weight': weights['recurring_mistake'] if is_recurring else weights['correction'],
                    })
                elif item.item_type == 'grammar':
                    item.write({'emphasis_weight': weights['grammar']})

            lesson.write({'state': 'analyzed', 'error_message': False})
        return True

    def _classify_vocab_item(self, item, entry_by_norm, review_by_entry, prior_by_norm, weights, known_due_today):
        self.ensure_one()
        entry = entry_by_norm.get(item.text_normalized)
        if entry is None:
            entry = self._find_dictionary_match(item.text_normalized, entry_by_norm)
        prior_item = prior_by_norm.get(item.text_normalized)

        if entry is not None:
            review = review_by_entry.get(entry.id)
            novelty = 'known' if (review and review.state == 'review') else 'seen'
            vals = {
                'entry_id': entry.id,
                'novelty': novelty,
                'seen_source': 'both' if prior_item else 'vocab',
                'srs_state_at_import': review.state if review else '',
                'emphasis_weight': weights['known'] if novelty == 'known' else weights['seen'],
            }
            if prior_item:
                vals['first_seen_lesson_id'] = prior_item.lesson_id.id
            item.write(vals)
            if novelty == 'known' and known_due_today and review and review.next_review_date:
                today = fields.Date.context_today(self)
                if review.next_review_date > today:
                    review.write({'next_review_date': today})
            return

        if prior_item is not None:
            item.write({
                'novelty': 'seen',
                'seen_source': 'previous_lesson',
                'first_seen_lesson_id': prior_item.lesson_id.id,
                'emphasis_weight': weights['seen'],
            })
            return

        entry_vals = {
            'type': 'phrase' if item.item_type == 'phrase' else 'word',
            'source_text': item.text,
            'source_language': self.language,
            'owner_id': self.user_id.id,
            'created_from': 'lesson_import',
        }
        if item.context:
            entry_vals['note'] = item.context

        try:
            new_entry = self.env['language.entry'].with_user(self.user_id).create(entry_vals)
        except ValidationError:
            # Dedup race — another item in the same batch (or a concurrent
            # save) already created this normalized entry. Attach to it
            # rather than crashing the whole analyze pass.
            new_entry = self.env['language.entry'].search([
                ('owner_id', '=', self.user_id.id),
                ('source_language', '=', self.language),
                ('normalized_text', '=', item.text_normalized),
            ], limit=1)
            if new_entry:
                entry_by_norm[new_entry.normalized_text] = new_entry
                item.write({
                    'entry_id': new_entry.id,
                    'novelty': 'seen',
                    'seen_source': 'vocab',
                    'emphasis_weight': weights['seen'],
                })
            return

        entry_by_norm[new_entry.normalized_text] = new_entry
        item.write({
            'entry_id': new_entry.id,
            'novelty': 'new',
            'seen_source': 'none',
            'emphasis_weight': weights['new'],
        })

    def _find_dictionary_match(self, normalized_text, entry_by_norm):
        """Longest-match sliding window — server-side port of the M34
        YouTube Vocab Radar cue matcher (ADR-033 § 34e / ADR-038 § 38d).

        Tries progressively shorter contiguous token windows; the first
        (i.e. longest) hit wins. A whole-text exact match is expected to
        have already been checked by the caller, so this only looks at
        strictly shorter windows.
        """
        tokens = (normalized_text or '').split()
        if len(tokens) <= 1:
            return None
        for window in range(len(tokens) - 1, 0, -1):
            for start in range(0, len(tokens) - window + 1):
                candidate = ' '.join(tokens[start:start + window])
                entry = entry_by_norm.get(candidate)
                if entry:
                    return entry
        return None

    # ------------------------------------------------------------------
    # Configurable emphasis weights (ADR-038 § 38b)
    # ------------------------------------------------------------------

    def _get_emphasis_weights(self):
        icp = self.env['ir.config_parameter'].sudo()

        def _int(key, default):
            try:
                return int(icp.get_param(key, default))
            except (TypeError, ValueError):
                return default

        return {
            'new': _int('language_lessons.weight.new', 3),
            'seen': _int('language_lessons.weight.seen', 2),
            'known': _int('language_lessons.weight.known', 1),
            'correction': _int('language_lessons.weight.correction', 3),
            'recurring_mistake': _int('language_lessons.weight.recurring_mistake', 4),
            'grammar': _int('language_lessons.weight.grammar', 2),
        }

    def _get_known_due_today(self):
        val = self.env['ir.config_parameter'].sudo().get_param('language_lessons.known_due_today', 'False')
        return str(val).strip().lower() in ('1', 'true', 'yes')
