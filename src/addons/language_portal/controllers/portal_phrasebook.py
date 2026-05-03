import importlib.util
import os

from odoo import http
from odoo.http import request

_PHRASEBOOK_PATH = os.path.join(os.path.dirname(__file__), "../data/phrasebook_data.py")


def _load_phrasebook():
    spec = importlib.util.spec_from_file_location("phrasebook_data", _PHRASEBOOK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PHRASEBOOK, mod.SCENARIO_ORDER


class PhrasebookPortal(http.Controller):

    @http.route('/phrasebook', type='http', auth='public', website=True)
    def phrasebook_index(self, **kw):
        phrasebook, order = _load_phrasebook()
        scenarios = [
            {"key": k, "icon": phrasebook[k]["icon"], "label": phrasebook[k]["label"],
             "count": len(phrasebook[k]["phrases"])}
            for k in order if k in phrasebook
        ]
        return request.render('language_portal.portal_phrasebook_index', {
            'scenarios': scenarios,
        })

    @http.route('/phrasebook/<string:scenario>', type='http', auth='public', website=True)
    def phrasebook_scenario(self, scenario, lang='en', **kw):
        phrasebook, order = _load_phrasebook()
        if scenario not in phrasebook:
            return request.not_found()
        data = phrasebook[scenario]
        active_lang = lang if lang in ('en', 'uk', 'el', 'pl') else 'en'
        return request.render('language_portal.portal_phrasebook_scenario', {
            'scenario_key': scenario,
            'scenario_label': data['label'],
            'scenario_icon': data['icon'],
            'phrases': data['phrases'],
            'active_lang': active_lang,
            'lang_labels': {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek', 'pl': 'Polish'},
        })
