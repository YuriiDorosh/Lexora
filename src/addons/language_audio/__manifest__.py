{
    'name': 'Language Audio',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Audio recording upload and TTS generation job lifecycle',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_words', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_audio.xml',
        'views/language_audio_views.xml',
        'views/portal_audio.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
