import importlib.util
import os
import random

from odoo import http
from odoo.http import request

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
        for ex in batch:
            choices = list(ex["choices"])
            random.shuffle(choices)
            ex = dict(ex)  # don't mutate the original

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
