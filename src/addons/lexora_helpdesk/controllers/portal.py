from odoo import http
from odoo.http import request


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
