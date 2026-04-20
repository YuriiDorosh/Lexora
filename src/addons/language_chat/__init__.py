from . import models, controllers  # noqa: F401


def _add_users_to_channels(env):
    """Add all Language Users as members of the public learning channels."""
    try:
        group = env.ref('language_security.group_language_user', raise_if_not_found=False)
        if not group:
            return
        Channel = env['discuss.channel'].sudo()
        channels = Channel.search([
            ('name', 'in', ['english', 'ukrainian', 'greek']),
            ('channel_type', '=', 'channel'),
        ])
        for channel in channels:
            existing_partner_ids = set(channel.channel_member_ids.mapped('partner_id').ids)
            for user in group.users:
                if user.partner_id.id not in existing_partner_ids:
                    channel.channel_member_ids.create({
                        'channel_id': channel.id,
                        'partner_id': user.partner_id.id,
                    })
    except Exception:
        pass  # non-fatal — users can join manually from Discuss


def post_init_hook(env):
    _add_users_to_channels(env)
