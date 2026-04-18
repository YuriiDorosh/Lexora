{
    'name': 'Language Anki Jobs',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Anki import job lifecycle and persistent import logs',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_words', 'language_security', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'views/language_anki_job_views.xml',
        'views/portal_anki.xml',
        'data/ir_cron_anki.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
