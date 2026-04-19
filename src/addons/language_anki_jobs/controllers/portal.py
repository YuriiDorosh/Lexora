"""Portal controller for Anki import jobs.

Routes:
  GET/POST /my/anki           — upload form
  GET      /my/anki/jobs      — import history list
  GET      /my/anki/jobs/<id> — job detail page
"""

import base64
import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager

_logger = logging.getLogger(__name__)

JOBS_PER_PAGE = 20
ALLOWED_EXTENSIONS = {'apkg', 'txt'}

ENTRY_TYPES = [
    ('word', 'Word'),
    ('phrase', 'Phrase'),
    ('sentence', 'Sentence'),
]


class AnkiPortal(CustomerPortal):
    """Portal pages for Anki deck import."""

    # ------------------------------------------------------------------
    # Portal home widget — shows import job count on /my
    # ------------------------------------------------------------------

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'anki_job_count' in counters:
            values['anki_job_count'] = request.env['language.anki.job'].search_count(
                [('user_id', '=', request.env.uid)]
            )
        return values

    # ------------------------------------------------------------------
    # Upload form  GET/POST /my/anki
    # ------------------------------------------------------------------

    @http.route('/my/anki', type='http', auth='user', website=True,
                methods=['GET', 'POST'])
    def anki_upload(self, **post):
        """Render the Anki deck upload form (GET) or process the upload (POST)."""
        Lang = request.env['language.lang'].sudo()
        languages = Lang.search([], order='name')

        if request.httprequest.method == 'POST':
            return self._handle_upload(post, languages)

        return request.render('language_anki_jobs.portal_anki_upload', {
            'page_name': 'anki_upload',
            'languages': languages,
            'entry_types': ENTRY_TYPES,
            'error': None,
            'post': {},
        })

    def _handle_upload(self, post, languages):
        """Process the multipart upload form and create the import job."""
        error = None
        uploaded = request.httprequest.files.get('deck_file')

        if not uploaded or not uploaded.filename:
            error = 'Please select a file to upload.'
        else:
            ext = uploaded.filename.rsplit('.', 1)[-1].lower() if '.' in uploaded.filename else ''
            if ext not in ALLOWED_EXTENSIONS:
                error = f'Unsupported file type ".{ext}". Please upload a .apkg or .txt file.'

        if not post.get('source_language_id'):
            error = error or 'Please select a source language.'

        if error:
            Lang = request.env['language.lang'].sudo()
            languages = Lang.search([], order='name')
            return request.render('language_anki_jobs.portal_anki_upload', {
                'page_name': 'anki_upload',
                'languages': languages,
                'entry_types': ENTRY_TYPES,
                'error': error,
                'post': post,
            })

        file_bytes = uploaded.read()
        file_b64 = base64.b64encode(file_bytes).decode('ascii')

        src_lang_id = int(post['source_language_id'])
        entry_type = post.get('entry_type', 'word')
        field_mapping_raw = post.get('field_mapping', '{}') or '{}'

        # Optional: destination language for immediate translations + PvP eligibility.
        tgt_lang_id_raw = post.get('target_language_id', '').strip()
        tgt_lang_id = int(tgt_lang_id_raw) if tgt_lang_id_raw else False
        is_pvp_eligible = bool(post.get('is_pvp_eligible'))

        # Validate: target language must differ from source language.
        if tgt_lang_id and tgt_lang_id == src_lang_id:
            tgt_lang_id = False

        try:
            Job = request.env['language.anki.job']
            job = Job.create({
                'filename': uploaded.filename,
                'file_format': ext,
                'file_data': file_b64,
                'file_name': uploaded.filename,
                'source_language_id': src_lang_id,
                'target_language_id': tgt_lang_id,
                'is_pvp_eligible': is_pvp_eligible,
                'entry_type': entry_type,
                'field_mapping': field_mapping_raw,
                'user_id': request.env.uid,
            })
            job.action_publish_import()
        except (UserError, Exception) as exc:
            _logger.error('Anki upload failed: %s', exc)
            Lang = request.env['language.lang'].sudo()
            languages = Lang.search([], order='name')
            return request.render('language_anki_jobs.portal_anki_upload', {
                'page_name': 'anki_upload',
                'languages': languages,
                'entry_types': ENTRY_TYPES,
                'error': f'Import failed: {exc}',
                'post': post,
            })

        return request.redirect(f'/my/anki/jobs/{job.id}')

    # ------------------------------------------------------------------
    # Import history  GET /my/anki/jobs
    # ------------------------------------------------------------------

    @http.route('/my/anki/jobs', type='http', auth='user', website=True)
    def anki_jobs_list(self, page=1, **kwargs):
        """Paginated list of the current user's import jobs."""
        Job = request.env['language.anki.job']
        domain = [('user_id', '=', request.env.uid)]
        total = Job.search_count(domain)

        pager = portal_pager(
            url='/my/anki/jobs',
            total=total,
            page=int(page),
            step=JOBS_PER_PAGE,
        )
        jobs = Job.search(
            domain,
            limit=JOBS_PER_PAGE,
            offset=pager['offset'],
            order='create_date desc',
        )

        return request.render('language_anki_jobs.portal_anki_jobs_list', {
            'jobs': jobs,
            'page_name': 'anki_jobs',
            'pager': pager,
            'total': total,
        })

    # ------------------------------------------------------------------
    # Job detail  GET /my/anki/jobs/<id>
    # ------------------------------------------------------------------

    @http.route('/my/anki/jobs/<int:job_id>', type='http', auth='user', website=True)
    def anki_job_detail(self, job_id, **kwargs):
        """Show status, counts, and skipped-items detail for one import job."""
        import json as _json

        Job = request.env['language.anki.job']
        job = Job.browse(job_id)
        if not job.exists() or job.user_id.id != request.env.uid:
            return request.not_found()

        skipped_items = []
        failed_items = []
        if job.details_log:
            try:
                log_data = _json.loads(job.details_log)
                skipped_items = log_data.get('skipped', [])
                failed_items = log_data.get('failed', [])
            except Exception:
                pass

        return request.render('language_anki_jobs.portal_anki_job_detail', {
            'job': job,
            'page_name': 'anki_jobs',
            'skipped_items': skipped_items,
            'failed_items': failed_items,
        })
