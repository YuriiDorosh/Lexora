from odoo import http
from odoo.http import request


class IdiomsPortal(http.Controller):

    @http.route('/idioms', type='http', auth='user', website=True)
    def idioms_index(self, language=None, category=None, level=None, **kw):
        domain = []
        if language:
            domain.append(('language', '=', language))
        if category:
            domain.append(('category', '=', category))
        if level:
            domain.append(('level', '=', level))

        idioms = request.env['language.idiom'].sudo().search(domain, order='language, level, expression')

        IdiomModel = request.env['language.idiom']
        languages = IdiomModel.fields_get(['language'])['language']['selection']
        categories = IdiomModel.fields_get(['category'])['category']['selection']
        levels = IdiomModel.fields_get(['level'])['level']['selection']

        return request.render('language_portal.portal_idioms_index', {
            'idioms': idioms,
            'languages': languages,
            'categories': categories,
            'levels': levels,
            'filter_language': language or '',
            'filter_category': category or '',
            'filter_level': level or '',
        })

    @http.route('/idioms/<int:idiom_id>', type='http', auth='user', website=True)
    def idioms_detail(self, idiom_id, **kw):
        idiom = request.env['language.idiom'].sudo().browse(idiom_id)
        if not idiom.exists():
            return request.not_found()
        return request.render('language_portal.portal_idioms_detail', {'idiom': idiom})
