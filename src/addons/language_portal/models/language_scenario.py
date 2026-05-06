from odoo import fields, models


class LanguageScenario(models.Model):
    _name = "language.scenario"
    _description = "AI Roleplay Scenario"
    _order = "sequence asc, id asc"

    name = fields.Char(required=True, translate=True)
    icon = fields.Char(default="💬")
    description = fields.Text(translate=True)
    difficulty = fields.Selection(
        [("A1", "A1 Beginner"), ("A2", "A2 Elementary"),
         ("B1", "B1 Intermediate"), ("B2", "B2 Upper-Intermediate"),
         ("C1", "C1 Advanced")],
        default="A2",
        required=True,
    )
    target_language = fields.Selection(
        [("en", "English"), ("uk", "Ukrainian"), ("el", "Greek"), ("pl", "Polish")],
        default="en",
        required=True,
    )
    initial_prompt = fields.Text(
        required=True,
        help="System prompt telling the LLM the scenario context and its role.",
    )
    sequence = fields.Integer(default=10)
    is_active = fields.Boolean(default=True)
    session_ids = fields.One2many("language.scenario.session", "scenario_id", string="Sessions")
    session_count = fields.Integer(compute="_compute_session_count", store=False)

    def _compute_session_count(self):
        for rec in self:
            rec.session_count = len(rec.session_ids)
