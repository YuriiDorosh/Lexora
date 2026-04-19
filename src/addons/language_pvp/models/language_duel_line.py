from odoo import fields, models


class LanguageDuelLine(models.Model):
    _name = 'language.duel.line'
    _description = 'PvP Duel Round Line'
    _order = 'duel_id, round_number'

    duel_id = fields.Many2one('language.duel', required=True, ondelete='cascade', index=True)
    player_id = fields.Many2one('res.users', required=True, ondelete='restrict')
    entry_id = fields.Many2one('language.entry', required=True, ondelete='restrict')
    round_number = fields.Integer(required=True)
    correct = fields.Boolean(default=False)
    answer_given = fields.Char(string='Answer Given')
    time_taken_seconds = fields.Float(string='Time (s)')
