import re
from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError


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
        [('draft', 'Draft'), ('pending', 'Pending Review'),
         ('published', 'Published'), ('rejected', 'Rejected')],
        default='draft', required=True, index=True,
    )
    author_id = fields.Many2one('res.users', string='Author',
                                default=lambda self: self.env.user,
                                ondelete='set null')
    language = fields.Selection(
        [('en', 'English'), ('uk', 'Ukrainian'), ('el', 'Greek'), ('pl', 'Polish')],
        default='en', required=True,
    )
    published_date = fields.Datetime()
    tag_ids = fields.Many2many('language.post.tag', string='Tags')
    comment_ids = fields.One2many('language.post.comment', 'post_id', string='Comments')
    comment_count = fields.Integer(compute='_compute_comment_count', store=False)

    @api.depends('comment_ids')
    def _compute_comment_count(self):
        for rec in self:
            rec.comment_count = len(rec.comment_ids)

    @api.depends('title')
    def _compute_slug(self):
        for rec in self:
            if rec.title:
                slug = rec.title.lower()
                slug = re.sub(r'[^\w\s-]', '', slug)
                slug = re.sub(r'[\s_]+', '-', slug).strip('-')
                rec.slug = slug[:80] or str(rec.id or 'post')
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

    def action_submit(self):
        for rec in self:
            if rec.status != 'draft':
                raise UserError('Only drafts can be submitted for review.')
            rec.status = 'pending'

    def action_approve(self):
        self._check_moderator()
        for rec in self:
            rec.sudo().write({
                'status': 'published',
                'published_date': rec.published_date or fields.Datetime.now(),
            })

    def action_reject(self):
        self._check_moderator()
        for rec in self:
            rec.sudo().status = 'rejected'

    def action_retract(self):
        """Author retracts a pending/rejected post back to draft."""
        for rec in self:
            if rec.author_id.id != self.env.user.id:
                raise AccessError('You can only retract your own posts.')
            if rec.status not in ('pending', 'rejected'):
                raise UserError('Only pending or rejected posts can be retracted.')
            rec.status = 'draft'

    def _check_moderator(self):
        if not self.env.user.has_group('language_security.group_language_moderator'):
            raise AccessError('Only moderators can approve or reject posts.')


class LanguagePostTag(models.Model):
    _name = 'language.post.tag'
    _description = 'Post Tag'
    _rec_name = 'name'

    name = fields.Char(required=True)
    color = fields.Integer(default=0)


class LanguagePostComment(models.Model):
    _name = 'language.post.comment'
    _description = 'Post Comment'
    _order = 'create_date asc, id asc'

    post_id = fields.Many2one('language.post', required=True, ondelete='cascade', index=True)
    author_id = fields.Many2one('res.users', required=True,
                                default=lambda self: self.env.user, ondelete='restrict')
    body = fields.Text(required=True)
    mention_ids = fields.Many2many('res.users', 'post_comment_mention_rel',
                                   'comment_id', 'user_id', string='Mentioned Users',
                                   compute='_compute_mentions', store=True)

    @api.depends('body')
    def _compute_mentions(self):
        User = self.env['res.users'].sudo()
        for rec in self:
            names = re.findall(r'@(\w+)', rec.body or '')
            if names:
                # Match login prefix (before @domain) or exact login
                found = User.browse()
                for name in names:
                    found |= User.search([
                        '|',
                        ('login', '=', name),
                        ('login', '=like', name + '@%'),
                    ])
                rec.mention_ids = found
            else:
                rec.mention_ids = User.browse()
