{
    'name': 'Language Portal',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Portal views, posts/articles/comments, copy-to-list inline UI',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_core', 'portal', 'website', 'website_require_login', 'website_menu_by_user_status'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
