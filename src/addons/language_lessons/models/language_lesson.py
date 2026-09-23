import logging
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.language_words.models.language_lang import LANGUAGE_SELECTION

from .lesson_parser import parse_lesson_text

_logger = logging.getLogger(__name__)

SOURCE_TYPE_SELECTION = [
    ('manual_text', 'Manual Text'),
    ('preply_extension', 'Preply Extension'),
    ('json_upload', 'JSON Upload'),
]

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('extracting', 'Extracting (AI)'),
    ('parsed', 'Parsed'),
    ('analyzed', 'Analyzed'),
    ('published', 'Published'),
    ('error', 'Error'),
]

PARSE_METHOD_SELECTION = [
    ('rule_based', 'Rule-based (markers found)'),
    ('llm', 'AI-extracted (no markers found)'),
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
    job_id = fields.Char(
        string='Job ID',
        readonly=True,
        copy=False,
        index=True,
        help='UUID for the in-flight lesson.extraction RabbitMQ job (ADR-018). '
             'Only set while state=extracting.',
    )
    parse_method = fields.Selection(
        selection=PARSE_METHOD_SELECTION,
        string='Parse Method',
        help='Which path produced the current item_ids: the deterministic '
             'marker parser, or the LLM extraction fallback for freeform '
             'canvas text with no recognisable markers (ADR-038 § 38g).',
    )

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
    # Parsing (ADR-038 § 38a rule-based fast path; § 38i async LLM
    # fallback for freeform/unmarked canvas text)
    # ------------------------------------------------------------------

    def action_parse(self):
        for lesson in self:
            try:
                parsed = parse_lesson_text(lesson.raw_payload)
            except Exception as exc:  # noqa: BLE001 — surface any parser bug as a visible job error
                lesson.write({'state': 'error', 'error_message': str(exc)})
                continue

            if parsed.get('markers_found'):
                lesson._apply_parsed_items(parsed, 'rule_based')
            else:
                # No Topic:/Vocab:/... markers anywhere in the pasted text —
                # this is real freeform canvas content (ADR-038 § 38g), not
                # a hand-typed quick note. Extraction over a whole document
                # can take minutes on CPU (§ 38i) — never block the request;
                # publish the job and let the cron-drained consumer apply
                # the result whenever it lands.
                lesson._enqueue_llm_extraction()
        return True

    def _apply_parsed_items(self, parsed, parse_method):
        """Create language.lesson.item rows from a {topic, items[]} result
        and advance state to 'parsed' (or 'error' if the LLM path found
        nothing usable). Shared by the sync rule-based path and the async
        extraction-completed handler so both end up in an identical state.
        """
        self.ensure_one()
        self.item_ids.unlink()

        vals = {'parse_method': parse_method}
        if (not self.name or self.name == 'New Lesson') and parsed.get('topic'):
            vals['name'] = parsed['topic']

        item_vals_list = [
            {
                'lesson_id': self.id,
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

        if not item_vals_list and parse_method == 'llm':
            # The LLM path found no markers AND extracted nothing — surface
            # this as an error rather than a silently-empty "analyzed"
            # lesson, so the user knows to retry / edit.
            self.write({
                'state': 'error',
                'parse_method': False,
                'error_message': (
                    'No recognisable structure found in this text, and AI '
                    'extraction returned nothing usable. Try adding explicit '
                    'markers (Topic:/Vocab:/Phrases:/Mistakes:/Grammar:/Notes:), '
                    'or click Re-parse to retry the AI extraction.'
                ),
            })
            return

        vals.update({'state': 'parsed', 'error_message': False, 'job_id': False})
        self.write(vals)

    def action_reparse(self):
        for lesson in self:
            lesson.item_ids.unlink()
            lesson.write({
                'state': 'draft', 'error_message': False,
                'job_id': False, 'parse_method': False,
            })
        return self.action_parse()

    # ------------------------------------------------------------------
    # Async LLM extraction (ADR-038 § 38i) — publish/consume, same shape
    # as language_translation's _enqueue_single / action_consume_results.
    # ------------------------------------------------------------------

    def _enqueue_llm_extraction(self):
        self.ensure_one()
        from odoo.addons.language_core.models.rabbitmq_publisher import RabbitMQPublisher  # noqa: PLC0415

        job_id = str(uuid.uuid4())
        self.write({'state': 'extracting', 'job_id': job_id, 'error_message': False})

        publisher = RabbitMQPublisher(self.env)
        publisher.publish(
            'lesson.extraction.requested',
            {
                'lesson_id': self.id,
                'raw_text': self.raw_payload or '',
                'language': self.language,
            },
            job_id=job_id,
        )

    def action_consume_extraction_results(self):
        """Drain lesson-extraction result queues — called by scheduled cron."""
        from odoo.addons.language_core.models.rabbitmq_consumer import RabbitMQConsumer  # noqa: PLC0415
        consumer = RabbitMQConsumer(self.env)
        consumer.drain('lesson.extraction.completed', self._handle_extraction_completed)
        consumer.drain('lesson.extraction.failed', self._handle_extraction_failed)

    def _handle_extraction_completed(self, job_id, payload):
        lesson = self._find_by_job_id(job_id)
        if not lesson:
            _logger.warning('lesson.extraction.completed: no record for job_id=%s', job_id)
            return
        if lesson.state != 'extracting':
            _logger.info(
                'lesson.extraction.completed: duplicate delivery for job_id=%s (state=%s) — skipped',
                job_id, lesson.state,
            )
            return

        raw_items = payload.get('items') if isinstance(payload, dict) else None
        items = []
        if isinstance(raw_items, list):
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                item_type = str(raw_item.get('item_type') or '').strip().lower()
                text = str(raw_item.get('text') or '').strip()
                if item_type not in ('vocab', 'phrase', 'correction', 'grammar', 'note') or not text:
                    continue

                def _opt(key):
                    val = raw_item.get(key)
                    val = str(val).strip() if val else ''
                    return val or None

                items.append({
                    'item_type': item_type,
                    'text': text[:300],
                    'translation_hint': _opt('translation_hint'),
                    'corrected_text': _opt('corrected_text'),
                    'context': _opt('context'),
                })

        topic = payload.get('topic') if isinstance(payload, dict) else None
        topic = topic.strip() if isinstance(topic, str) and topic.strip() else None

        lesson.sudo()._apply_parsed_items({'topic': topic, 'items': items}, 'llm')
        if lesson.state == 'parsed':
            try:
                lesson.action_analyze_novelty()
            except UserError as exc:
                lesson.write({'state': 'error', 'error_message': str(exc)})
        _logger.info('lesson.extraction.completed: lesson_id=%s job_id=%s items=%d',
                     lesson.id, job_id, len(items))

    def _handle_extraction_failed(self, job_id, payload):
        lesson = self._find_by_job_id(job_id)
        if not lesson:
            _logger.warning('lesson.extraction.failed: no record for job_id=%s', job_id)
            return
        if lesson.state != 'extracting':
            _logger.info(
                'lesson.extraction.failed: duplicate delivery for job_id=%s (state=%s) — skipped',
                job_id, lesson.state,
            )
            return
        lesson.sudo().write({
            'state': 'error',
            'parse_method': False,
            'error_message': (
                'AI extraction failed: '
                + str((payload or {}).get('error', 'unknown error'))
                + '. Click Re-parse to try again, or add explicit Topic:/'
                  'Vocab:/... markers to skip AI extraction entirely.'
            ),
        })
        _logger.warning('lesson.extraction.failed: lesson_id=%s job_id=%s error=%s',
                         lesson.id, job_id, (payload or {}).get('error'))

    def _find_by_job_id(self, job_id):
        return self.sudo().search([('job_id', '=', job_id)], limit=1) or None

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
