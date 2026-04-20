"""Portal controllers for chat features.

Routes:
  GET  /my/users/<id>              — public profile of another user
  POST /my/users/<id>/dm           — get or create DM channel, redirect to Discuss
  JSON /my/vocabulary/add_from_chat — save selected text as a vocabulary entry
"""

import logging

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

LANG_NAMES = {'en': 'English', 'uk': 'Ukrainian', 'el': 'Greek'}


def _try_detect_language(text: str):
    """Return 'en', 'uk', 'el', or None using langdetect (same logic as language_words)."""
    try:
        from langdetect import detect_langs
        results = detect_langs(text)
        best = results[0] if results else None
        if best and best.prob >= 0.7 and best.lang in ('en', 'uk', 'el'):
            return best.lang
    except Exception:
        pass
    return None


class ChatPortal(http.Controller):

    # ------------------------------------------------------------------
    # GET /my/users/<id> — public user profile
    # ------------------------------------------------------------------

    @http.route('/my/users/<int:user_id>', type='http', auth='user', website=True, methods=['GET'])
    def user_public_profile(self, user_id, **kw):
        uid = request.env.user.id

        target_user = request.env['res.users'].sudo().browse(user_id)
        if not target_user.exists() or not target_user.active:
            return request.not_found()

        Profile = request.env['language.user.profile'].sudo()
        profile = Profile.search([('user_id', '=', user_id)], limit=1)

        # Global rank
        rank = None
        if profile and profile.xp_total > 0:
            rank = Profile.search_count([('xp_total', '>', profile.xp_total)]) + 1

        return request.render('language_chat.portal_user_public_profile', {
            'target_user': target_user,
            'profile':     profile,
            'rank':        rank,
            'lang_names':  LANG_NAMES,
            'is_own':      uid == user_id,
        })

    # ------------------------------------------------------------------
    # POST /my/users/<id>/dm — create / open DM channel
    # ------------------------------------------------------------------

    @http.route('/my/users/<int:user_id>/dm', type='http', auth='user', website=True, methods=['POST'])
    def start_dm(self, user_id, **kw):
        me = request.env.user
        target = request.env['res.users'].sudo().browse(user_id)
        if not target.exists() or user_id == me.id:
            return request.redirect('/discuss')

        partner_ids = [me.partner_id.id, target.partner_id.id]
        Channel = request.env['discuss.channel'].sudo()

        try:
            # channel_get finds or creates a canonical 1-to-1 chat channel
            channel_info = Channel.with_user(me).channel_get(partner_ids)
            channel_id = channel_info.get('id') if isinstance(channel_info, dict) else channel_info.id
        except Exception as exc:
            _logger.warning('DM channel creation failed: %s', exc)
            return request.redirect('/discuss')

        return request.redirect(f'/discuss/channel/{channel_id}')

    # ------------------------------------------------------------------
    # JSON /my/vocabulary/add_from_chat — save highlighted text
    # ------------------------------------------------------------------

    @http.route('/my/vocabulary/add_from_chat', type='json', auth='user', website=True)
    def add_from_chat(self, text='', source_language=None, **kw):
        text = (text or '').strip()
        if not text or len(text) > 500:
            return {'status': 'error', 'message': 'Invalid text length.'}

        uid = request.env.user.id

        # Detect language if not supplied by client
        if not source_language or source_language not in ('en', 'uk', 'el'):
            source_language = _try_detect_language(text)

        if not source_language:
            # Fall back to user's default source language
            profile = request.env['language.user.profile'].sudo().search(
                [('user_id', '=', uid)], limit=1,
            )
            source_language = (
                profile.default_source_language
                or (profile.learning_languages[:1].code if profile.learning_languages else 'en')
            )

        Entry = request.env['language.entry'].sudo()
        try:
            entry = Entry.create({
                'source_text':    text,
                'source_language': source_language,
                'owner_id':       uid,
                'type':           'word' if len(text.split()) == 1 else 'phrase',
                'created_from':   'copied_from_chat',
            })
            _logger.info('add_from_chat: created entry %d for user %d', entry.id, uid)
            return {'status': 'ok', 'entry_id': entry.id, 'source_language': source_language}
        except ValidationError:
            return {'status': 'duplicate'}
        except Exception as exc:
            _logger.warning('add_from_chat failed for user %d: %s', uid, exc)
            return {'status': 'error', 'message': str(exc)}
