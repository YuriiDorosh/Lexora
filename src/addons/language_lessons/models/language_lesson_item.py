from odoo import api, fields, models

from odoo.addons.language_words.models.normalize import normalize

ITEM_TYPE_SELECTION = [
    ('vocab', 'Vocabulary'),
    ('phrase', 'Phrase'),
    ('correction', 'Correction'),
    ('grammar', 'Grammar'),
    ('note', 'Note'),
]

NOVELTY_SELECTION = [
    ('new', 'New'),
    ('seen', 'Seen'),
    ('known', 'Known'),
    ('none', 'N/A'),
]

SEEN_SOURCE_SELECTION = [
    ('vocab', 'Vocabulary'),
    ('previous_lesson', 'Previous Lesson'),
    ('both', 'Both'),
    ('none', 'None'),
]


class LanguageLessonItem(models.Model):
    _name = 'language.lesson.item'
    _description = 'Lesson Item (vocab / phrase / correction / grammar / note)'
    _order = 'lesson_id, sequence, id'

    lesson_id = fields.Many2one(
        comodel_name='language.lesson',
        string='Lesson',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    item_type = fields.Selection(
        selection=ITEM_TYPE_SELECTION,
        string='Type',
        required=True,
        index=True,
    )
    text = fields.Char(string='Text', required=True)
    text_normalized = fields.Char(
        string='Normalized Text',
        compute='_compute_text_normalized',
        store=True,
        index=True,
    )
    translation_hint = fields.Char(string='Translation Hint')
    corrected_text = fields.Text(string='Corrected Text')
    context = fields.Text(string='Context Sentence')

    entry_id = fields.Many2one(
        comodel_name='language.entry',
        string='Vocabulary Entry',
        ondelete='set null',
        index=True,
    )
    novelty = fields.Selection(
        selection=NOVELTY_SELECTION,
        string='Novelty',
        default='none',
        index=True,
    )
    seen_source = fields.Selection(
        selection=SEEN_SOURCE_SELECTION,
        string='Seen Source',
        default='none',
    )
    first_seen_lesson_id = fields.Many2one(
        comodel_name='language.lesson',
        string='First Seen In',
        ondelete='set null',
    )
    srs_state_at_import = fields.Char(string='SRS State At Import')
    emphasis_weight = fields.Integer(string='Emphasis Weight', default=0)
    is_recurring_mistake = fields.Boolean(string='Recurring Mistake', default=False)

    @api.depends('text')
    def _compute_text_normalized(self):
        for item in self:
            item.text_normalized = normalize(item.text or '')
