import random
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

SUPPORTED_LANGS = ['en', 'uk', 'el']


class LanguageWordOfDay(models.Model):
    _name = 'language.word.of.day'
    _description = 'Word of the Day'
    _order = 'selected_date desc'
    _rec_name = 'word_text'

    language = fields.Selection(
        [('en', 'English'), ('uk', 'Ukrainian'), ('el', 'Greek')],
        required=True, index=True,
    )
    entry_id = fields.Many2one('language.entry', ondelete='set null')
    word_text = fields.Char(string='Word', required=True)
    translation_text = fields.Char(string='Translation')
    selected_date = fields.Date(required=True, default=fields.Date.today, index=True)

    _sql_constraints = [
        ('unique_lang_date', 'UNIQUE(language, selected_date)', 'One word per language per day.'),
    ]

    @api.model
    def _pick_word_of_day(self):
        """Cron: select a new word for each language for today."""
        today = fields.Date.today()
        Entry = self.env['language.entry'].sudo()
        Translation = self.env['language.translation'].sudo() if 'language.translation' in self.env.registry else None

        for lang in SUPPORTED_LANGS:
            existing = self.search([('language', '=', lang), ('selected_date', '=', today)], limit=1)
            if existing:
                continue

            # Prefer shared pvp_eligible entries with translations
            domain = [
                ('source_language', '=', lang),
                ('status', '=', 'active'),
                ('is_shared', '=', True),
                ('pvp_eligible', '=', True),
            ]
            candidates = Entry.search(domain, limit=100)
            if not candidates:
                domain = [('source_language', '=', lang), ('status', '=', 'active'), ('pvp_eligible', '=', True)]
                candidates = Entry.search(domain, limit=100)
            if not candidates:
                domain = [('source_language', '=', lang), ('status', '=', 'active')]
                candidates = Entry.search(domain, limit=100)

            if not candidates:
                continue

            entry = random.choice(candidates)
            translation = ''
            if Translation:
                # pick English translation preferably
                target = 'en' if lang != 'en' else 'uk'
                trans_rec = Translation.search([
                    ('entry_id', '=', entry.id),
                    ('target_language', '=', target),
                    ('status', '=', 'completed'),
                ], limit=1)
                if trans_rec:
                    translation = trans_rec.translated_text

            try:
                self.create({
                    'language': lang,
                    'entry_id': entry.id,
                    'word_text': entry.source_text,
                    'translation_text': translation,
                    'selected_date': today,
                })
            except Exception as exc:
                _logger.warning('Word of day creation failed for %s: %s', lang, exc)

    @api.model
    def get_today(self, language='en'):
        today = fields.Date.today()
        rec = self.search([('language', '=', language), ('selected_date', '=', today)], limit=1)
        if not rec:
            # Trigger selection and try again
            self._pick_word_of_day()
            rec = self.search([('language', '=', language), ('selected_date', '=', today)], limit=1)
        return rec
