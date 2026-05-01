from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class SupportPortal(http.Controller):

    @http.route("/support", type="http", auth="public", website=True, sitemap=True)
    def support_form(self, **kw):
        return request.render("lexora_helpdesk.portal_support_form", {})

    @http.route(
        "/support/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def support_submit(self, name="", description="", **kw):
        name = (name or "").strip()
        description = (description or "").strip()

        if not name or not description:
            return request.render(
                "lexora_helpdesk.portal_support_form",
                {
                    "error": "Both Subject and Message are required.",
                    "name": name,
                    "description": description,
                },
            )

        vals = {"name": name, "description": description}
        if not request.env.user._is_public():
            vals["user_id"] = request.env.user.id

        request.env["lexora.ticket"].sudo().create(vals)
        return request.render("lexora_helpdesk.portal_support_thanks", {})


class TicketCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "ticket_count" in counters:
            values["ticket_count"] = (
                request.env["lexora.ticket"]
                .sudo()
                .search_count([("user_id", "=", request.env.user.id)])
            )
        return values

    @http.route(
        ["/my/tickets", "/my/tickets/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_tickets(self, page=1, **kw):
        Ticket = request.env["lexora.ticket"].sudo()
        domain = [("user_id", "=", request.env.user.id)]
        ticket_count = Ticket.search_count(domain)

        pager = portal_pager(
            url="/my/tickets",
            total=ticket_count,
            page=page,
            step=10,
        )

        tickets = Ticket.search(domain, limit=10, offset=pager["offset"], order="create_date desc")

        return request.render(
            "lexora_helpdesk.portal_ticket_list",
            {
                "tickets": tickets,
                "pager": pager,
                "page_name": "ticket",
            },
        )

    @http.route("/my/tickets/<int:ticket_id>", type="http", auth="user", website=True)
    def portal_ticket_detail(self, ticket_id, **kw):
        ticket = (
            request.env["lexora.ticket"]
            .sudo()
            .search([("id", "=", ticket_id), ("user_id", "=", request.env.user.id)], limit=1)
        )
        if not ticket:
            return request.not_found()

        return request.render(
            "lexora_helpdesk.portal_ticket_detail",
            {
                "ticket": ticket,
                "page_name": "ticket",
            },
        )
