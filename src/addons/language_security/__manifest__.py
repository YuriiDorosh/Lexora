{
    'name': 'Language Security',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Security groups and access rules for Lexora language learning platform',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['base', 'portal', 'password_security'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
