from odoo import fields, models


REASON_LABELS = {
    'duel_win':  'Duel Win',
    'duel_loss': 'Duel Loss',
    'duel_draw': 'Duel Draw',
    'practice':  'Practice',
    'bonus':     'Bonus',
    'initial':   'Initial Balance',
}


class LanguageXpLog(models.Model):
    _name = 'language.xp.log'
    _description = 'XP Transaction Log'
    _order = 'date desc, id desc'

    user_id = fields.Many2one(
        'res.users', required=True, ondelete='cascade', index=True,
    )
    amount = fields.Integer(required=True, help='Positive = gain, negative = loss.')
    reason = fields.Selection(
        [(k, v) for k, v in REASON_LABELS.items()],
        required=True,
    )
    # Soft reference — no FK so language_learning doesn't depend on language_pvp
    duel_id = fields.Integer(string='Duel ID', index=True)
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    note = fields.Char()
