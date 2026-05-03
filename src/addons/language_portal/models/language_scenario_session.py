import json

from odoo import api, fields, models


class LanguageScenarioSession(models.Model):
    _name = "language.scenario.session"
    _description = "AI Roleplay Session"
    _order = "write_date desc, id desc"

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade", index=True)
    scenario_id = fields.Many2one("language.scenario", required=True, ondelete="cascade")
    target_language = fields.Selection(
        [("en", "English"), ("uk", "Ukrainian"), ("el", "Greek"), ("pl", "Polish")],
        required=True,
    )
    chat_history = fields.Text(default="[]")
    created_at = fields.Datetime(default=fields.Datetime.now)
    message_count = fields.Integer(compute="_compute_message_count", store=False)

    def _compute_message_count(self):
        for rec in self:
            try:
                rec.message_count = len(json.loads(rec.chat_history or "[]"))
            except Exception:
                rec.message_count = 0

    def get_history(self):
        try:
            return json.loads(self.chat_history or "[]")
        except Exception:
            return []

    def append_message(self, role: str, content: str):
        history = self.get_history()
        history.append({"role": role, "content": content})
        self.write({"chat_history": json.dumps(history)})

    @api.model
    def get_or_create_session(self, scenario_id, user_id):
        session = self.sudo().search([
            ("scenario_id", "=", scenario_id),
            ("user_id", "=", user_id),
        ], order="id desc", limit=1)
        if not session:
            scenario = self.env["language.scenario"].sudo().browse(scenario_id)
            session = self.sudo().create({
                "scenario_id": scenario_id,
                "user_id": user_id,
                "target_language": scenario.target_language,
            })
        return session
