import importlib.util
import logging
import os
import random

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_EXERCISES_PATH = os.path.join(os.path.dirname(__file__), "../data/cloze_exercises.py")


def _load_exercises():
    spec = importlib.util.spec_from_file_location("cloze_exercises", _EXERCISES_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CLOZE_EXERCISES, mod.CATEGORIES, mod.LEVELS, mod.LANGUAGES


class GrammarPracticePortal(http.Controller):

    @http.route("/my/grammar-practice", type="http", auth="user", website=True, methods=["GET"])
    def grammar_practice(self, lang="en", category=None, level=None, **kw):
        exercises, categories, levels, languages = _load_exercises()

        # Filter
        pool = [e for e in exercises if e["language"] == lang]
        if category:
            pool = [e for e in pool if e["category"] == category]
        if level:
            pool = [e for e in pool if e["level"] == level]

        # Pick a random batch of 10 exercises
        batch = random.sample(pool, min(10, len(pool))) if pool else []

        # Shuffle choices for each exercise so the answer isn't always first
        shuffled = []
        for ex in batch:
            ex_copy = dict(ex)
            choices = list(ex_copy["choices"])
            random.shuffle(choices)
            ex_copy["choices"] = choices
            shuffled.append(ex_copy)
        batch = shuffled

        available_categories = sorted({e["category"] for e in exercises if e["language"] == lang})

        return request.render("language_portal.portal_grammar_practice", {
            "exercises": batch,
            "categories": categories,
            "available_categories": available_categories,
            "levels": levels,
            "languages": languages,
            "active_lang": lang,
            "active_category": category or "",
            "active_level": level or "",
            "total_pool": len(pool),
            "page_name": "grammar_practice",
        })

    @http.route("/my/grammar-practice/score", type="json", auth="user", methods=["POST"])
    def grammar_practice_score(self, correct_count=0, **kw):
        try:
            correct_count = max(0, int(correct_count))
        except (TypeError, ValueError):
            correct_count = 0

        xp_gained = 0
        if correct_count <= 0:
            return {"xp_gained": 0}

        uid = request.env.user.id
        _logger.info("GrammarXP: user=%s correct=%s — attempting award", uid, correct_count)

        if "language.xp.log" in request.env.registry:
            try:
                xp_gained = correct_count * 5
                request.env["language.xp.log"].sudo().create({
                    "user_id": uid,
                    "amount": xp_gained,
                    "reason": "grammar_practice",
                    "note": f"{correct_count} correct in grammar practice",
                })
                profile = request.env["language.user.profile"].sudo().search(
                    [("user_id", "=", uid)], limit=1
                )
                if profile:
                    profile.write({"xp_total": profile.xp_total + xp_gained})
                    _logger.info("GrammarXP: awarded %s XP to user %s (xp_total=%s)", xp_gained, uid, profile.xp_total)
                else:
                    _logger.warning("GrammarXP: no profile for user %s — log created but total not updated", uid)
            except Exception as exc:
                _logger.exception("GrammarXP: failed for user %s: %s", uid, exc)
                xp_gained = 0
        else:
            _logger.warning("GrammarXP: language.xp.log not in registry — XP skipped")

        return {"xp_gained": xp_gained}
