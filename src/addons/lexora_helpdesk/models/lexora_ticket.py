import json
import logging

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

_STUB_REPLY = (
    "Thank you for contacting Lexora Support! "
    "Your ticket has been received and our AI is reviewing it. "
    "You can also check the Grammar Guide (/grammar) and Vocabulary sections for self-service help. "
    "We'll follow up if further assistance is needed."
)


class LexoraTicket(models.Model):
    _name = "lexora.ticket"
    _description = "Lexora Support Ticket"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "name"

    name = fields.Char(
        string="Subject",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Message",
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Submitted by",
        tracking=True,
        ondelete="set null",
    )
    state = fields.Selection(
        [("new", "New"), ("closed", "Closed")],
        string="Status",
        default="new",
        required=True,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Override create — fire AI auto-reply for every new ticket
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        for ticket in tickets:
            self._ai_auto_reply(ticket)
        return tickets

    def action_close(self):
        self.write({"state": "closed"})

    def action_reopen(self):
        self.write({"state": "new"})

    # ------------------------------------------------------------------
    # AI auto-reply
    # ------------------------------------------------------------------

    def _ai_auto_reply(self, ticket):
        """Call ai_mentor /answer and post the reply as an OdooBot comment."""
        ICP = self.env["ir.config_parameter"].sudo()

        if ICP.get_param("lexora.ai_mentor.enabled", "1") == "0":
            return

        service_url = ICP.get_param(
            "lexora.ai_mentor.url", "http://ai-mentor-service:8000"
        )
        timeout = int(ICP.get_param("lexora.ai_mentor.timeout", "35"))

        description = (ticket.description or "").strip()[:2000]

        try:
            resp = requests.post(
                f"{service_url}/answer",
                json={
                    "ticket_id": ticket.id,
                    "subject": ticket.name,
                    "description": description,
                    "language": "en",
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = json.loads(resp.content.decode("utf-8", errors="replace"))
            reply = str(data.get("reply") or "").strip() or _STUB_REPLY
            _logger.info(
                "ai_mentor replied to ticket #%d (rag_used=%s, sources=%d)",
                ticket.id,
                data.get("rag_used"),
                len(data.get("sources", [])),
            )
        except requests.exceptions.Timeout:
            _logger.warning(
                "ai_mentor timeout (%ds) for ticket #%d — using stub reply",
                timeout,
                ticket.id,
            )
            reply = _STUB_REPLY
        except Exception as exc:
            _logger.error(
                "ai_mentor error for ticket #%d: %s — using stub reply",
                ticket.id,
                exc,
            )
            reply = _STUB_REPLY

        self._post_bot_message(ticket, reply)

    def _post_bot_message(self, ticket, body: str):
        """Post body as a visible chatter comment without triggering outbound emails."""
        try:
            bot_partner = self.env.ref("base.partner_root")
            ticket.sudo().with_context(
                mail_post_autofollow=False,
                mail_create_nosubscribe=True,
                mail_notify_force_send=False,
            ).message_post(
                body=body,
                author_id=bot_partner.id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        except Exception as exc:
            _logger.error(
                "Failed to post OdooBot reply to ticket #%d: %s", ticket.id, exc
            )
