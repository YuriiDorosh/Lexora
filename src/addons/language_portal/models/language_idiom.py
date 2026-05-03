from odoo import fields, models


class LanguageIdiom(models.Model):
    _name = 'language.idiom'
    _description = 'Idiom'
    _order = 'language asc, level asc, expression asc'

    expression = fields.Char(required=True, index=True)
    literal_meaning = fields.Char()
    idiomatic_meaning = fields.Text(required=True)
    example = fields.Text()
    origin_note = fields.Text()
    language = fields.Selection(
        [('en', 'English'), ('uk', 'Ukrainian'), ('el', 'Greek'), ('pl', 'Polish')],
        required=True, index=True,
    )
    category = fields.Selection([
        ('daily_life', 'Daily Life'),
        ('work', 'Work & Career'),
        ('emotions', 'Emotions'),
        ('relationships', 'Relationships'),
        ('learning', 'Learning'),
        ('communication', 'Communication'),
    ], required=True)
    level = fields.Selection(
        [('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1'),
         ('B2', 'B2'), ('C1', 'C1'), ('C2', 'C2')],
        required=True,
    )
