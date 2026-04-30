import json
import logging

import requests

from odoo import models

_logger = logging.getLogger(__name__)

_STUB_REPLY = (
    "Thank you for contacting Lexora Support! "
    "Your ticket has been received and our AI is looking into it. "
    "You can also check the Grammar Guide (/grammar) and Vocabulary sections for self-service help. "
    "We'll follow up shortly if further assistance is needed."
)


class TicketHelpdeskAI(models.Model):
    """Extends odoo_website_helpdesk's ticket.helpdesk to inject an OdooBot
    auto-reply on every new ticket via the ai_mentor RAG service."""

    _inherit = "ticket.helpdesk"

    # ------------------------------------------------------------------
    # Override create() — fire AI auto-reply for every new ticket
    # ------------------------------------------------------------------

    def create(self, vals_list):
        tickets = super().create(vals_list)
        for ticket in tickets:
            self._ai_auto_reply(ticket)
        return tickets

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    def _ai_auto_reply(self, ticket):
        """Call ai_mentor /answer and post the reply as a real OdooBot message
        (message_type='comment') so the ticket owner receives a notification."""
        ICP = self.env["ir.config_parameter"].sudo()

        enabled = ICP.get_param("language.ai_mentor.enabled", "1")
        if enabled == "0":
            return

        service_url = ICP.get_param("language.ai_mentor.url", "http://ai-mentor-service:8000")
        timeout = int(ICP.get_param("language.ai_mentor.timeout", "35"))

        # ticket.helpdesk uses 'subject' for the human-readable title;
        # 'name' is the auto-generated sequence number (e.g. HD0001).
        subject = ticket.subject or ticket.name or "No subject"
        description = self._extract_description(ticket)

        try:
            resp = requests.post(
                f"{service_url}/answer",
                json={
                    "ticket_id": ticket.id,
                    "subject": subject,
                    "description": description,
                    "language": "en",
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            raw = resp.content.decode("utf-8", errors="replace")
            data = json.loads(raw)
            reply = str(data.get("reply") or "").strip()
            rag_used = bool(data.get("rag_used", False))
            sources = data.get("sources", [])

            if not reply:
                reply = _STUB_REPLY

            _logger.info(
                "ai_mentor replied to ticket #%d subject=%r (rag_used=%s, sources=%d)",
                ticket.id, subject[:60], rag_used, len(sources),
            )
        except requests.exceptions.Timeout:
            _logger.warning(
                "ai_mentor timeout (%ds) for ticket #%d — using stub reply",
                timeout, ticket.id,
            )
            reply = _STUB_REPLY
        except Exception as exc:
            _logger.error(
                "ai_mentor error for ticket #%d: %s — using stub reply",
                ticket.id, exc,
            )
            reply = _STUB_REPLY

        self._post_bot_message(ticket, reply)

    def _extract_description(self, ticket):
        """Return plain-text description; handles HTML body and empty values."""
        desc = ticket.description or ""
        if "<" in desc:
            try:
                from lxml import html as lxml_html
                desc = lxml_html.fromstring(desc).text_content()
            except Exception:
                pass
        return desc.strip()[:2000]

    def _post_bot_message(self, ticket, body: str):
        """Post body as a real comment (not a note) so the ticket creator
        receives an email/notification via Odoo's standard mail.thread flow."""
        try:
            bot_partner = self.env.ref("base.partner_root")
            ticket.sudo().message_post(
                body=body,
                author_id=bot_partner.id,
                # 'comment' = visible message that triggers follower notifications.
                # 'note' = internal note visible only to internal users — NOT what we want.
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        except Exception as exc:
            _logger.error(
                "Failed to post OdooBot reply to ticket #%d: %s", ticket.id, exc
            )
