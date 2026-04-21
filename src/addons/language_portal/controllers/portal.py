"""Portal controllers for language_portal.

Public routes  (auth='public'):
  GET  /             — homepage (word of day, recent articles, stats)
  GET  /posts        — published articles list (paginated)
  GET  /posts/<slug> — article detail with comments + copy-to-list JS

Authenticated routes (auth='user'):
  GET  /my/posts                  — author's own posts (all statuses)
  GET  /my/posts/new              — create draft form
  POST /my/posts/new              — save new draft
  GET  /my/posts/<id>/edit        — edit draft form
  POST /my/posts/<id>/edit        — save edits
  POST /my/posts/<id>/submit      — draft → pending
  POST /my/posts/<id>/retract     — pending/rejected → draft
  POST /my/posts/<id>/comment     — add comment to a published post
  POST /my/posts/<id>/delete_comment/<cid> — author/mod delete comment

Moderator routes (auth='user', guard inside):
  GET  /my/moderation             — pending posts queue
  POST /my/posts/<id>/approve     — pending → published
  POST /my/posts/<id>/reject      — pending → rejected

JSON route:
  POST /my/posts/<id>/copy_text   — copy selected text to vocabulary
"""

import logging
from odoo import http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

LANG_NAMES = {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek'}
_PER_PAGE = 9


def _detect_language(text):
    try:
        from langdetect import detect_langs
        results = detect_langs(text)
        best = results[0] if results else None
        if best and best.prob >= 0.7 and best.lang in ('en', 'uk', 'el'):
            return best.lang
    except Exception:
        pass
    return None


def _build_stats(env):
    stats = {}
    try:
        stats['total_entries'] = env['language.entry'].sudo().search_count(
            [('status', '=', 'active')])
    except Exception:
        stats['total_entries'] = 0
    try:
        stats['total_users'] = env['language.user.profile'].sudo().search_count([])
    except Exception:
        stats['total_users'] = 0
    try:
        stats['total_translations'] = (
            env['language.translation'].sudo().search_count([('status', '=', 'completed')])
            if 'language.translation' in env.registry else 0
        )
    except Exception:
        stats['total_translations'] = 0
    return stats


def _is_moderator():
    return request.env.user.has_group('language_security.group_language_moderator')


class PortalHome(http.Controller):

    # ------------------------------------------------------------------
    # Public: homepage
    # ------------------------------------------------------------------

    @http.route('/', type='http', auth='public', website=True, methods=['GET'])
    def homepage(self, **kw):
        env = request.env
        word_of_day = None
        if 'language.word.of.day' in env.registry:
            word_of_day = env['language.word.of.day'].sudo().get_today('en')
        articles = []
        if 'language.post' in env.registry:
            articles = env['language.post'].sudo().search(
                [('status', '=', 'published')], limit=3, order='published_date desc')
        stats = _build_stats(env)
        return request.render('language_portal.homepage', {
            'word_of_day': word_of_day,
            'articles': articles,
            'stats': stats,
            'lang_names': LANG_NAMES,
        })

    # ------------------------------------------------------------------
    # Public: article listing
    # ------------------------------------------------------------------

    @http.route(['/posts', '/posts/page/<int:page>'],
                type='http', auth='public', website=True, methods=['GET'])
    def articles_list(self, page=1, lang=None, tag=None, **kw):
        Post = request.env['language.post'].sudo()
        domain = [('status', '=', 'published')]
        if lang and lang in ('en', 'uk', 'el'):
            domain.append(('language', '=', lang))
        if tag:
            tag_rec = request.env['language.post.tag'].sudo().search(
                [('name', '=ilike', tag)], limit=1)
            if tag_rec:
                domain.append(('tag_ids', 'in', tag_rec.ids))

        total = Post.search_count(domain)
        offset = (int(page) - 1) * _PER_PAGE
        posts = Post.search(domain, limit=_PER_PAGE, offset=offset,
                            order='published_date desc')
        total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
        all_tags = request.env['language.post.tag'].sudo().search([])
        return request.render('language_portal.portal_posts_list', {
            'posts': posts,
            'total': total,
            'page': int(page),
            'total_pages': total_pages,
            'all_tags': all_tags,
            'lang_filter': lang,
            'tag_filter': tag,
            'lang_names': LANG_NAMES,
        })

    # ------------------------------------------------------------------
    # Public: article detail
    # ------------------------------------------------------------------

    @http.route('/posts/<string:slug>', type='http', auth='public', website=True,
                methods=['GET'])
    def article_detail(self, slug, **kw):
        post = request.env['language.post'].sudo().search(
            [('slug', '=', slug), ('status', '=', 'published')], limit=1)
        if not post:
            return request.not_found()
        user = request.env.user
        is_author = not user._is_public() and post.author_id.id == user.id
        return request.render('language_portal.portal_post_detail', {
            'post': post,
            'comments': post.comment_ids,
            'is_author': is_author,
            'is_moderator': _is_moderator(),
            'lang_names': LANG_NAMES,
        })

    # ------------------------------------------------------------------
    # Authenticated: author's post list
    # ------------------------------------------------------------------

    @http.route('/my/posts', type='http', auth='user', website=True, methods=['GET'])
    def my_posts(self, **kw):
        posts = request.env['language.post'].sudo().search(
            [('author_id', '=', request.env.user.id)], order='id desc')
        return request.render('language_portal.portal_my_posts', {
            'posts': posts,
            'lang_names': LANG_NAMES,
        })

    # ------------------------------------------------------------------
    # Authenticated: create new post
    # ------------------------------------------------------------------

    @http.route('/my/posts/new', type='http', auth='user', website=True,
                methods=['GET', 'POST'])
    def post_new(self, **kw):
        if request.httprequest.method == 'POST':
            return self._save_post(None, kw)
        all_tags = request.env['language.post.tag'].sudo().search([])
        return request.render('language_portal.portal_post_form', {
            'post': None,
            'all_tags': all_tags,
            'lang_names': LANG_NAMES,
            'errors': {},
            'post_data': {},
        })

    # ------------------------------------------------------------------
    # Authenticated: edit existing post
    # ------------------------------------------------------------------

    @http.route('/my/posts/<int:post_id>/edit', type='http', auth='user', website=True,
                methods=['GET', 'POST'])
    def post_edit(self, post_id, **kw):
        post = request.env['language.post'].sudo().browse(post_id).exists()
        if not post or post.author_id.id != request.env.user.id:
            return request.not_found()
        if post.status not in ('draft', 'rejected'):
            return request.redirect(f'/my/posts?error=not_editable')
        if request.httprequest.method == 'POST':
            return self._save_post(post, kw)
        all_tags = request.env['language.post.tag'].sudo().search([])
        return request.render('language_portal.portal_post_form', {
            'post': post,
            'all_tags': all_tags,
            'lang_names': LANG_NAMES,
            'errors': {},
            'post_data': {},
        })

    def _save_post(self, post, data):
        title = (data.get('title') or '').strip()
        body = (data.get('body') or '').strip()
        language = data.get('language', 'en')
        tag_ids_raw = data.get('tag_ids') or []
        if isinstance(tag_ids_raw, str):
            tag_ids_raw = [tag_ids_raw]
        tag_ids = []
        for t in tag_ids_raw:
            try:
                tag_ids.append(int(t))
            except (ValueError, TypeError):
                pass

        errors = {}
        if not title:
            errors['title'] = 'Title is required.'
        if not body:
            errors['body'] = 'Body is required.'
        if language not in ('en', 'uk', 'el'):
            errors['language'] = 'Invalid language.'

        if errors:
            all_tags = request.env['language.post.tag'].sudo().search([])
            return request.render('language_portal.portal_post_form', {
                'post': post,
                'all_tags': all_tags,
                'lang_names': LANG_NAMES,
                'errors': errors,
                'post_data': data,
            })

        vals = {
            'title': title,
            'body': body,
            'language': language,
            'tag_ids': [(6, 0, tag_ids)],
        }
        if post:
            post.sudo().write(vals)
        else:
            vals['author_id'] = request.env.user.id
            vals['status'] = 'draft'
            post = request.env['language.post'].sudo().create(vals)

        return request.redirect(f'/my/posts?saved={post.id}')

    # ------------------------------------------------------------------
    # Authenticated: submit for review
    # ------------------------------------------------------------------

    @http.route('/my/posts/<int:post_id>/submit', type='http', auth='user', website=True,
                methods=['POST'])
    def post_submit(self, post_id, **kw):
        post = request.env['language.post'].sudo().browse(post_id).exists()
        if not post or post.author_id.id != request.env.user.id:
            return request.not_found()
        try:
            post.with_user(request.env.user).action_submit()
        except (UserError, AccessError) as e:
            return request.redirect(f'/my/posts?error={e}')
        return request.redirect('/my/posts?submitted=1')

    # ------------------------------------------------------------------
    # Authenticated: retract to draft
    # ------------------------------------------------------------------

    @http.route('/my/posts/<int:post_id>/retract', type='http', auth='user', website=True,
                methods=['POST'])
    def post_retract(self, post_id, **kw):
        post = request.env['language.post'].sudo().browse(post_id).exists()
        if not post or post.author_id.id != request.env.user.id:
            return request.not_found()
        try:
            post.with_user(request.env.user).action_retract()
        except (UserError, AccessError):
            pass
        return request.redirect('/my/posts')

    # ------------------------------------------------------------------
    # Moderator: pending queue
    # ------------------------------------------------------------------

    @http.route('/my/moderation', type='http', auth='user', website=True, methods=['GET'])
    def moderation_queue(self, **kw):
        if not _is_moderator():
            return request.redirect('/my')
        pending = request.env['language.post'].sudo().search(
            [('status', '=', 'pending')], order='id asc')
        return request.render('language_portal.portal_moderation', {
            'pending_posts': pending,
            'lang_names': LANG_NAMES,
        })

    # ------------------------------------------------------------------
    # Moderator: approve
    # ------------------------------------------------------------------

    @http.route('/my/posts/<int:post_id>/approve', type='http', auth='user', website=True,
                methods=['POST'])
    def post_approve(self, post_id, **kw):
        if not _is_moderator():
            return request.redirect('/my')
        post = request.env['language.post'].sudo().browse(post_id).exists()
        if not post:
            return request.not_found()
        try:
            post.sudo().action_approve()
        except (UserError, AccessError):
            pass
        return request.redirect('/my/moderation?approved=1')

    # ------------------------------------------------------------------
    # Moderator: reject
    # ------------------------------------------------------------------

    @http.route('/my/posts/<int:post_id>/reject', type='http', auth='user', website=True,
                methods=['POST'])
    def post_reject(self, post_id, **kw):
        if not _is_moderator():
            return request.redirect('/my')
        post = request.env['language.post'].sudo().browse(post_id).exists()
        if not post:
            return request.not_found()
        try:
            post.sudo().action_reject()
        except (UserError, AccessError):
            pass
        return request.redirect('/my/moderation?rejected=1')

    # ------------------------------------------------------------------
    # Authenticated: add comment
    # ------------------------------------------------------------------

    @http.route('/my/posts/<int:post_id>/comment', type='http', auth='user', website=True,
                methods=['POST'])
    def post_comment(self, post_id, **kw):
        post = request.env['language.post'].sudo().browse(post_id).exists()
        if not post or post.status != 'published':
            return request.not_found()
        body = (kw.get('body') or '').strip()
        if body:
            request.env['language.post.comment'].sudo().create({
                'post_id': post.id,
                'author_id': request.env.user.id,
                'body': body,
            })
        return request.redirect(f'/posts/{post.slug}#comments')

    # ------------------------------------------------------------------
    # Author/mod: delete comment
    # ------------------------------------------------------------------

    @http.route('/my/posts/<int:post_id>/delete_comment/<int:comment_id>',
                type='http', auth='user', website=True, methods=['POST'])
    def delete_comment(self, post_id, comment_id, **kw):
        comment = request.env['language.post.comment'].sudo().browse(comment_id).exists()
        if not comment:
            return request.not_found()
        uid = request.env.user.id
        is_own = comment.author_id.id == uid
        if not is_own and not _is_moderator():
            return request.redirect(f'/posts/{comment.post_id.slug}')
        post_slug = comment.post_id.slug
        comment.sudo().unlink()
        return request.redirect(f'/posts/{post_slug}#comments')

    # ------------------------------------------------------------------
    # JSON: copy text from post to vocabulary
    # ------------------------------------------------------------------

    @http.route('/my/posts/<int:post_id>/copy_text', type='json', auth='user', website=True)
    def copy_text_from_post(self, post_id, text='', source_language=None, **kw):
        text = (text or '').strip()
        if not text or len(text) > 500:
            return {'status': 'error', 'message': 'Invalid text length.'}

        post = request.env['language.post'].sudo().browse(post_id).exists()
        if not post or post.status != 'published':
            return {'status': 'error', 'message': 'Post not found.'}

        if not source_language or source_language not in ('en', 'uk', 'el'):
            source_language = _detect_language(text)
        if not source_language:
            source_language = post.language

        uid = request.env.user.id
        Entry = request.env['language.entry'].sudo()
        try:
            entry = Entry.create({
                'source_text': text,
                'source_language': source_language,
                'owner_id': uid,
                'type': 'word' if len(text.split()) == 1 else 'phrase',
                'created_from': 'copied_from_post',
                'copied_from_post_id': post.id,
            })
            return {'status': 'ok', 'entry_id': entry.id, 'source_language': source_language}
        except ValidationError:
            return {'status': 'duplicate'}
        except Exception as exc:
            _logger.warning('copy_text_from_post failed: %s', exc)
            return {'status': 'error', 'message': str(exc)}
