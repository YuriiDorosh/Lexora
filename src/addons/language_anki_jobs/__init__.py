from . import models, controllers

# ---------------------------------------------------------------------------
# Website menu hooks
# ---------------------------------------------------------------------------
# The XML data file (data/website_menus.xml) adds the menus to the "Default
# Main Menu" (website_id=False), which acts as the template for new websites.
# These hooks ensure the same menus are also added to every *existing* website
# when the module is first installed or updated — covering databases that were
# set up before this module existed.

_LEXORA_MENUS = [
    # (external_id_suffix, name, url, sequence)
    ('vocabulary', 'My Vocabulary', '/my/vocabulary', 50),
    ('anki',       'Import Anki',   '/my/anki',        60),
]


def _ensure_website_menus(env):
    """Add Lexora navbar items to every existing website if not already present."""
    Menu = env['website.menu']
    for website in env['website'].search([]):
        top_menu = Menu.search(
            [('parent_id', '=', False), ('website_id', '=', website.id)],
            limit=1,
        )
        if not top_menu:
            continue
        for _suffix, name, url, seq in _LEXORA_MENUS:
            already = Menu.search([('url', '=', url), ('website_id', '=', website.id)], limit=1)
            if not already:
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
