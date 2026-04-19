from . import models, controllers

# ---------------------------------------------------------------------------
# Website menu hooks — propagate navbar entry to all existing websites
# ---------------------------------------------------------------------------

_PRACTICE_MENU = ('practice', 'Daily Practice', '/my/practice', 55)


def _ensure_website_menus(env):
    Menu = env['website.menu']
    for website in env['website'].search([]):
        top_menu = Menu.search(
            [('parent_id', '=', False), ('website_id', '=', website.id)],
            limit=1,
        )
        if not top_menu:
            continue
        _suffix, name, url, seq = _PRACTICE_MENU
        if not Menu.search([('url', '=', url), ('website_id', '=', website.id)], limit=1):
            Menu.create({
                'name': name,
                'url': url,
                'parent_id': top_menu.id,
                'website_id': website.id,
                'sequence': seq,
                'user_logged': True,
            })


def post_init_hook(env):
    _ensure_website_menus(env)


def post_update_hook(env):
    _ensure_website_menus(env)
