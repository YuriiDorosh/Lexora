import re
from odoo import api, fields, models
from odoo.exceptions import UserError


class LanguagePost(models.Model):
    _name = 'language.post'
    _description = 'Language Learning Article / Post'
    _order = 'published_date desc, id desc'
    _rec_name = 'title'

    title = fields.Char(required=True, translate=False)
    slug = fields.Char(compute='_compute_slug', store=True, index=True)
    body = fields.Html(required=True, sanitize_tags=True)
    summary = fields.Text(compute='_compute_summary', store=True)
    status = fields.Selection(
        [('draft', 'Draft'), ('published', 'Published')],
        default='published', required=True, index=True,
    )
    author_id = fields.Many2one('res.users', string='Author', default=lambda self: self.env.user)
    language = fields.Selection(
        [('en', 'English'), ('uk', 'Ukrainian'), ('el', 'Greek')],
        default='en', required=True,
    )
    published_date = fields.Datetime(default=fields.Datetime.now)
    tag_ids = fields.Many2many('language.post.tag', string='Tags')

    @api.depends('title')
    def _compute_slug(self):
        for rec in self:
            if rec.title:
                slug = rec.title.lower()
                slug = re.sub(r'[^\w\s-]', '', slug)
                slug = re.sub(r'[\s_]+', '-', slug).strip('-')
                rec.slug = slug[:80]
            else:
                rec.slug = ''

    @api.depends('body')
    def _compute_summary(self):
        for rec in self:
            if rec.body:
                clean = re.sub(r'<[^>]+>', ' ', rec.body or '')
                clean = re.sub(r'\s+', ' ', clean).strip()
                rec.summary = clean[:300]
            else:
                rec.summary = ''


class LanguagePostTag(models.Model):
    _name = 'language.post.tag'
    _description = 'Post Tag'
    _rec_name = 'name'

    name = fields.Char(required=True)
    color = fields.Integer(default=0)
