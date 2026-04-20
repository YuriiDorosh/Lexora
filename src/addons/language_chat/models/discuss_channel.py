import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

PUBLIC_CHANNEL_NAMES = ('english', 'ukrainian', 'greek')
DEFAULT_KEEP = 1000


class DiscussChannelGC(models.Model):
    _inherit = 'discuss.channel'

    @api.model
    def _gc_chat_history(self, keep=DEFAULT_KEEP):
        """Nightly: keep only the N most recent messages in each public language channel."""
        channels = self.sudo().search([
            ('name', 'in', list(PUBLIC_CHANNEL_NAMES)),
            ('channel_type', '=', 'channel'),
        ])
        Message = self.env['mail.message'].sudo()
        for channel in channels:
            recent_ids = Message.search(
                [('model', '=', 'discuss.channel'), ('res_id', '=', channel.id)],
                limit=keep,
                order='id desc',
            ).ids
            if len(recent_ids) < keep:
                continue  # Fewer messages than the limit — nothing to prune
            old = Message.search([
                ('model', '=', 'discuss.channel'),
                ('res_id', '=', channel.id),
                ('id', 'not in', recent_ids),
            ])
            count = len(old)
            if count:
                old.unlink()
                _logger.info(
                    'chat GC: pruned %d messages from #%s (kept %d)',
                    count, channel.name, keep,
                )
