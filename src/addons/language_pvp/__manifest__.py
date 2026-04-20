{
    'name': 'Language PvP',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Asynchronous PvP word duels: challenge, play, earn XP. M9.',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_words', 'language_translation', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/website_menus.xml',
        'views/portal_arena.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
