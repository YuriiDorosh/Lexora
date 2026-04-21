from odoo import api, fields, models


class LanguageSeededWord(models.Model):
    _name = 'language.seeded.word'
    _description = '3000 Most Common English Words'
    _order = 'sort_order asc, word asc'

    word = fields.Char(required=True, index=True)
    level = fields.Selection(
        [('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1'),
         ('B2', 'B2'), ('C1', 'C1'), ('C2', 'C2')],
        required=True, index=True,
    )
    pos = fields.Char('Part of Speech')
    pos_code = fields.Char('POS Code', help='Short code: n/v/adj/adv/prep/conj/pron/det')
    translation_uk = fields.Char('Ukrainian')
    translation_el = fields.Char('Greek')
    sort_order = fields.Integer(default=0, index=True)
    translation_status = fields.Selection(
        [('pending', 'Pending'), ('done', 'Done'), ('failed', 'Failed')],
        default='done',
    )

    _sql_constraints = [
        ('unique_word_level', 'UNIQUE(word, level)', 'This word already exists at this CEFR level.'),
    ]

    @api.model
    def _seed_from_json(self, words_data):
        """Idempotent seed: inserts words not already present. Called from post-init hook."""
        existing = set(
            (r.word.lower(), r.level)
            for r in self.sudo().search([])
        )
        to_create = []
        for w in words_data:
            key = (w.get('word', '').lower(), w.get('level', ''))
            if key not in existing:
                to_create.append({
                    'word': w['word'],
                    'level': w['level'],
                    'pos': w.get('pos', ''),
                    'pos_code': w.get('pos_code', ''),
                    'translation_uk': w.get('translation_uk', ''),
                    'translation_el': w.get('translation_el', ''),
                    'sort_order': w.get('sort_order', 0),
                    'translation_status': 'done' if w.get('translation_uk') else 'pending',
                })
        if to_create:
            self.sudo().create(to_create)
        return len(to_create)
