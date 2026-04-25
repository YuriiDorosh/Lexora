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
    return mod.CLOZE_EXERCISES, mod.LANGUAGES


def _tokenise(sentence):
    """Split on whitespace; preserve punctuation attached to words."""
    return sentence.split()


def _normalise(text):
    return " ".join(text.strip().lower().split()).rstrip(".,!?;:")


class SentenceBuilderPortal(http.Controller):

    @http.route("/my/sentence-builder", type="http", auth="user", website=True, methods=["GET"])
    def sentence_builder(self, lang="en", level=None, **kw):
        exercises, languages = _load_exercises()

        pool = [e for e in exercises if e["language"] == lang]
        if level:
            pool = [e for e in pool if e["level"] == level]

        # Keep only sentences with at least 5 tokens
        pool = [e for e in pool if len(_tokenise(e["sentence"])) >= 5]

        batch_raw = random.sample(pool, min(5, len(pool))) if pool else []

        sentences = []
        for ex in batch_raw:
            tokens = _tokenise(ex["sentence"])
            shuffled = tokens[:]
            # Ensure shuffle is different from original
            for _ in range(10):
                random.shuffle(shuffled)
                if shuffled != tokens:
                    break
            sentences.append({
                "original": ex["sentence"],
                "tokens": tokens,
                "shuffled": shuffled,
                "level": ex.get("level", ""),
                "category": ex.get("category", ""),
            })

        levels = sorted({e["level"] for e in exercises if e["language"] == lang and e["level"]})

        return request.render("language_portal.portal_sentence_builder", {
            "sentences": sentences,
            "languages": languages,
            "levels": levels,
            "active_lang": lang,
            "active_level": level or "",
            "total_pool": len(pool),
            "page_name": "sentence_builder",
        })

    @http.route("/my/sentence-builder/score", type="json", auth="user", methods=["POST"])
    def sentence_builder_score(self, correct_count=0, **kw):
        try:
            correct_count = max(0, int(correct_count))
        except (TypeError, ValueError):
            correct_count = 0

        if correct_count <= 0:
            return {"xp_gained": 0}

        xp_gained = 0
        uid = request.env.user.id
        _logger.info("SentenceBuilderXP: user=%s correct=%s — attempting award", uid, correct_count)

        if "language.xp.log" in request.env.registry:
            try:
                xp_gained = correct_count * 10
                request.env["language.xp.log"].sudo().create({
                    "user_id": uid,
                    "amount": xp_gained,
                    "reason": "grammar_practice",
                    "note": f"{correct_count} correct sentences in Sentence Builder",
                })
                profile = request.env["language.user.profile"].sudo().search(
                    [("user_id", "=", uid)], limit=1
                )
                if profile:
                    profile.write({"xp_total": profile.xp_total + xp_gained})
                    _logger.info("SentenceBuilderXP: awarded %s XP to user %s", xp_gained, uid)
            except Exception as exc:
                _logger.exception("SentenceBuilderXP: failed for user %s: %s", uid, exc)
                xp_gained = 0
        else:
            _logger.warning("SentenceBuilderXP: language.xp.log not in registry — XP skipped")

        return {"xp_gained": xp_gained}
