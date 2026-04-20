{
    'name': 'Language Chat',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Public channels, private DMs, save-to-vocabulary from chat',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_core', 'language_words', 'mail', 'portal', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'data/chat_channels.xml',
        'data/website_menus.xml',
        'views/portal_chat.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
}
