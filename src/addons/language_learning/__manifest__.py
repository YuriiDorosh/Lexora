{
    'name': 'Language Learning — SRS',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Spaced Repetition System (SM-2) for vocabulary review. M7.',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_words', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/ir_cron_srs.xml',
        'views/language_review_views.xml',
        'views/portal_practice.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
