{
    'name': 'Language Translation',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Translation model and async job lifecycle (Argos Translate via RabbitMQ)',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_words', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/translation_record_rules.xml',
        'data/ir_cron_translation.xml',
        'views/language_translation_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
