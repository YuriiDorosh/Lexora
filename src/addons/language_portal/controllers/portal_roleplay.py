import logging
import os

import requests as _requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

LLM_SVC = os.environ.get("LLM_SERVICE_URL", "http://llm-service:8000")


class RoleplayPortal(http.Controller):

    @http.route("/my/roleplay", type="http", auth="user", website=True, methods=["GET"])
    def roleplay_grid(self, **kw):
        env = request.env
        scenarios = env["language.scenario"].sudo().search([("is_active", "=", True)])
        return request.render("language_portal.portal_roleplay_grid", {
            "scenarios": scenarios,
            "page_name": "roleplay",
        })

    @http.route("/my/roleplay/<int:scenario_id>", type="http", auth="user", website=True, methods=["GET"])
    def roleplay_session(self, scenario_id, **kw):
        env = request.env
        scenario = env["language.scenario"].sudo().browse(scenario_id)
        if not scenario.exists() or not scenario.is_active:
            return request.not_found()
        session = env["language.scenario.session"].sudo().get_or_create_session(
            scenario_id, request.env.user.id
        )
        history = session.get_history()
        return request.render("language_portal.portal_roleplay_chat", {
            "scenario": scenario,
            "session": session,
            "history": history,
            "page_name": "roleplay",
        })

    @http.route("/my/roleplay/<int:scenario_id>/send", type="json", auth="user", methods=["POST"])
    def roleplay_send(self, scenario_id, message="", **kw):
        env = request.env
        scenario = env["language.scenario"].sudo().browse(scenario_id)
        if not scenario.exists():
            return {"status": "error", "message": "Scenario not found"}

        message = (message or "").strip()
        if not message:
            return {"status": "error", "message": "Empty message"}

        session = env["language.scenario.session"].sudo().get_or_create_session(
            scenario_id, request.env.user.id
        )
        history = session.get_history()

        history_payload = [{"role": m["role"], "content": m["content"]} for m in history]

        reply = ""
        try:
            _logger.info("Roleplay[%s]: POST %s/roleplay", scenario_id, LLM_SVC)
            resp = _requests.post(
                f"{LLM_SVC}/roleplay",
                json={
                    "system_prompt": scenario.initial_prompt or "",
                    "history": history_payload,
                    "user_message": message,
                    "target_language": scenario.target_language or "en",
                },
                timeout=90,
            )
            _logger.info("Roleplay[%s]: status=%s", scenario_id, resp.status_code)
            resp.raise_for_status()
            # Decode bytes explicitly — avoids any content-type detection issue
            import json as _json
            raw = resp.content.decode("utf-8", errors="replace")
            _logger.info("Roleplay[%s]: body=%s", scenario_id, raw[:300])
            data = _json.loads(raw)
            reply = str(data.get("reply") or "").strip()
        except Exception as exc:
            _logger.exception("Roleplay[%s]: call failed: %s", scenario_id, exc)
            reply = ""

        if not reply:
            reply = "I'm sorry, I couldn't respond right now. Please try again!"

        session.append_message("user", message)
        session.append_message("assistant", reply)

        return {"status": "ok", "reply": reply}

    @http.route("/my/roleplay/<int:scenario_id>/reset", type="http", auth="user", website=True, methods=["POST"])
    def roleplay_reset(self, scenario_id, **kw):
        env = request.env
        session = env["language.scenario.session"].sudo().search([
            ("scenario_id", "=", scenario_id),
            ("user_id", "=", request.env.user.id),
        ], limit=1)
        if session:
            session.write({"chat_history": "[]"})
        return request.redirect(f"/my/roleplay/{scenario_id}")
