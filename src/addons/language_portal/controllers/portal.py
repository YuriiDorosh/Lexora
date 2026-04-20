import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalHome(http.Controller):

    # ------------------------------------------------------------------
    # GET / — public homepage (overrides Odoo default)
    # GET /posts — article listing
    # GET /posts/<slug> — article detail
    # ------------------------------------------------------------------

    @http.route('/', type='http', auth='public', website=True, methods=['GET'])
    def homepage(self, **kw):
        env = request.env

        # Word of the Day (en)
        word_of_day = None
        if 'language.word.of.day' in env.registry:
            word_of_day = env['language.word.of.day'].sudo().get_today('en')

        # Latest 3 published articles
        articles = []
        if 'language.post' in env.registry:
            articles = env['language.post'].sudo().search(
                [('status', '=', 'published')], limit=3, order='published_date desc'
            )

        # Global stats
        stats = _build_stats(env)

        return request.render('language_portal.homepage', {
            'word_of_day': word_of_day,
            'articles': articles,
            'stats': stats,
        })

    @http.route('/posts', type='http', auth='public', website=True, methods=['GET'])
    def articles_list(self, page=1, **kw):
        Post = request.env['language.post'].sudo()
        total = Post.search_count([('status', '=', 'published')])
        per_page = 9
        offset = (int(page) - 1) * per_page
        posts = Post.search([('status', '=', 'published')], limit=per_page, offset=offset,
                            order='published_date desc')
        total_pages = max(1, (total + per_page - 1) // per_page)
        return request.render('language_portal.portal_posts_list', {
            'posts': posts,
            'total': total,
            'page': int(page),
            'total_pages': total_pages,
        })

    @http.route('/posts/<string:slug>', type='http', auth='public', website=True, methods=['GET'])
    def article_detail(self, slug, **kw):
        post = request.env['language.post'].sudo().search(
            [('slug', '=', slug), ('status', '=', 'published')], limit=1
        )
        if not post:
            return request.not_found()
        return request.render('language_portal.portal_post_detail', {'post': post})


def _build_stats(env):
    stats = {}
    try:
        stats['total_entries'] = env['language.entry'].sudo().search_count([('status', '=', 'active')])
    except Exception:
        stats['total_entries'] = 0
    try:
        stats['total_users'] = env['language.user.profile'].sudo().search_count([])
    except Exception:
        stats['total_users'] = 0
    try:
        stats['total_translations'] = env['language.translation'].sudo().search_count(
            [('status', '=', 'completed')]
        ) if 'language.translation' in env.registry else 0
    except Exception:
        stats['total_translations'] = 0
    return stats
