import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_URL_RE = re.compile(
    r'^https?://'          # http or https
    r'(?:[a-zA-Z0-9\-]+\.)+'  # domain
    r'[a-zA-Z]{2,}'        # TLD
    r'(?:[/?#]\S*)?$',     # optional path/query/fragment
    re.IGNORECASE,
)


class LanguageMediaLink(models.Model):
    """External URL attached to a learning entry or post (SPEC §3.7).

    At least one of ``entry_id`` or ``post_id`` must be set.
    No server-side reachability checks; no OG-tag scraping in MVP.
    """

    _name = 'language.media.link'
    _description = 'Media Link'
    _rec_name = 'url'

    entry_id = fields.Many2one(
        comodel_name='language.entry',
        string='Entry',
        ondelete='cascade',
        index=True,
    )
    # post_id — deferred to M7 (language.post not yet defined)

    url = fields.Char(string='URL', required=True)
    title = fields.Char(string='Title')
    description = fields.Text(string='Description')
    user_note = fields.Text(string='User Note')

    @api.constrains('url')
    def _check_url_format(self):
        for link in self:
            if not _URL_RE.match(link.url or ''):
                raise ValidationError(
                    f'Invalid URL "{link.url}". '
                    'Please enter a full URL starting with http:// or https://'
                )
