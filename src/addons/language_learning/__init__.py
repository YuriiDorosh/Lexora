from . import models, controllers

# ---------------------------------------------------------------------------
# Website menu hooks — propagate navbar entry to all existing websites
# ---------------------------------------------------------------------------

_NAVBAR_MENUS = [
    ('Daily Practice', '/my/practice', 55),
    ('My Profile',     '/my/dashboard', 65),
    ('Leaderboard',    '/my/leaderboard', 70),
]


def _ensure_website_menus(env):
    Menu = env['website.menu']
    for website in env['website'].search([]):
        top_menu = Menu.search(
            [('parent_id', '=', False), ('website_id', '=', website.id)],
            limit=1,
        )
        if not top_menu:
            continue
        for name, url, seq in _NAVBAR_MENUS:
            if not Menu.search([('url', '=', url), ('website_id', '=', website.id)], limit=1):
                Menu.create({
                    'name': name,
                    'url': url,
                    'parent_id': top_menu.id,
                    'website_id': website.id,
                    'sequence': seq,
                    'user_logged': True,
                })


def _seed_xp_logs(env):
    """Create one 'initial' XP log entry for users who already have XP but no log."""
    Profile = env['language.user.profile'].sudo()
    Log = env['language.xp.log'].sudo()
    for profile in Profile.search([('xp_total', '>', 0)]):
        if not Log.search([('user_id', '=', profile.user_id.id)], limit=1):
            Log.create({
                'user_id': profile.user_id.id,
                'amount':  profile.xp_total,
                'reason':  'initial',
                'note':    'Balance at module install',
            })


def post_init_hook(env):
    _ensure_website_menus(env)
    _seed_xp_logs(env)


def post_update_hook(env):
    _ensure_website_menus(env)
    _seed_xp_logs(env)
